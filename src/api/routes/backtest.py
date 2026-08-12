from typing import Literal

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.data.database import db_manager

router = APIRouter()


class BacktestTrade(BaseModel):
    tenor: str
    commodity: str
    valuation_date: str
    expiry_date: str
    ns_price: float
    entry_price: float
    signal: str
    exit_valuation_date: str
    exit_price: float
    pnl: float


class BacktestSummary(BaseModel):
    tenor: str
    trade_count: int
    total_pnl: float
    win_rate: float
    average_pnl: float


class BacktestResponse(BaseModel):
    trades: list[BacktestTrade]
    summary: list[BacktestSummary]


def nelson_siegel(t: float, beta0: float, beta1: float, beta2: float, lmbda: float) -> float:
    """Calculates model price for maturity t (in years)."""
    if t <= 0:
        t = 1e-6

    factor1 = (1 - np.exp(-lmbda * t)) / (lmbda * t)
    factor2 = factor1 - np.exp(-lmbda * t)
    return float(beta0 + beta1 * factor1 + beta2 * factor2)


def _run_tenor_backtest(params_df: pd.DataFrame, fwd_df: pd.DataFrame, months_out: int) -> pd.DataFrame:
    """
    Backtests the NS-vs-actual signal for a single tenor (e.g. M+2 or M+3):
    buy at valuation date m when the model price is below the actual price (sell when above),
    then close the same contract one month later at its then-current actual price.
    """
    df = params_df.copy()
    df["expiry_date"] = df["valuation_date"] + pd.DateOffset(months=months_out)
    t_years = (df["expiry_date"] - df["valuation_date"]).dt.days / 365.25
    df["ns_price"] = [
        nelson_siegel(t, b0, b1, b2, lm)
        for t, b0, b1, b2, lm in zip(t_years, df["beta0"], df["beta1"], df["beta2"], df["lmbda"])
    ]

    # Entry: actual market price for the same contract on the valuation date
    entry = fwd_df.rename(columns={"price": "entry_price"})
    df = df.merge(entry, on=["valuation_date", "commodity", "expiry_date"], how="inner")

    # Exit: one month later, look up the same contract (now closer to expiry) to close the position
    df["exit_valuation_date"] = df["valuation_date"] + pd.DateOffset(months=1)
    exit_prices = fwd_df.rename(columns={"valuation_date": "exit_valuation_date", "price": "exit_price"})
    df = df.merge(exit_prices, on=["exit_valuation_date", "commodity", "expiry_date"], how="inner")

    df["signal"] = np.where(df["ns_price"] < df["entry_price"], "BUY", "SELL")
    df["pnl"] = np.where(
        df["signal"] == "BUY",
        df["exit_price"] - df["entry_price"],
        df["entry_price"] - df["exit_price"],
    )
    df["tenor"] = f"M+{months_out}"
    return df


@router.get("/backtest/nelson_siegel_pnl", response_model=BacktestResponse)
def get_nelson_siegel_backtest(
    tenor: Literal["M2", "M3", "both"] = Query("both", description="Which forward tenor(s) to backtest"),
    commodity: str = Query("Crude Oil", description="Commodity to backtest"),
):
    params_df = db_manager.get_all_nelson_siegel_parameters(commodity)
    fwd_df = db_manager.get_all_forward_prices(commodity)

    if params_df.empty or fwd_df.empty:
        raise HTTPException(status_code=404, detail="No data available to run the backtest.")

    params_df["valuation_date"] = pd.to_datetime(params_df["valuation_date"])
    fwd_df["valuation_date"] = pd.to_datetime(fwd_df["valuation_date"])
    fwd_df["expiry_date"] = pd.to_datetime(fwd_df["expiry_date"])
    # Guard against duplicate ingestion runs re-inserting the same contract quote
    fwd_df = fwd_df.drop_duplicates(subset=["valuation_date", "commodity", "expiry_date"], keep="first")

    months_to_run = {"M2": [2], "M3": [3], "both": [2, 3]}[tenor]

    results = [_run_tenor_backtest(params_df, fwd_df, m) for m in months_to_run]
    combined = pd.concat(results, ignore_index=True).sort_values(["tenor", "valuation_date"])

    if combined.empty:
        raise HTTPException(status_code=404, detail="No completed trades found for the selected tenor(s).")

    trades = [
        BacktestTrade(
            tenor=row.tenor,
            commodity=row.commodity,
            valuation_date=row.valuation_date.strftime("%Y-%m-%d"),
            expiry_date=row.expiry_date.strftime("%Y-%m-%d"),
            ns_price=round(row.ns_price, 4),
            entry_price=round(row.entry_price, 4),
            signal=row.signal,
            exit_valuation_date=row.exit_valuation_date.strftime("%Y-%m-%d"),
            exit_price=round(row.exit_price, 4),
            pnl=round(row.pnl, 4),
        )
        for row in combined.itertuples()
    ]

    summary = [
        BacktestSummary(
            tenor=tenor_label,
            trade_count=len(group),
            total_pnl=round(group["pnl"].sum(), 4),
            win_rate=round((group["pnl"] > 0).mean() * 100, 2),
            average_pnl=round(group["pnl"].mean(), 4),
        )
        for tenor_label, group in combined.groupby("tenor")
    ]

    return BacktestResponse(trades=trades, summary=summary)
