from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from  src.data.database import db_manager
import pandas as pd
import numpy as np

router = APIRouter()

class forward_prices(BaseModel):
    valuation_date: str
    commodity: str
    expiry_date: str
    price: float

class ForwardPriceEstimate(BaseModel):
    valuation_date: str
    expiry_date: str
    tenor: str  # e.g., 'M+1', 'M+2'
    time_to_maturity_years: float
    estimated_price: float

def nelson_siegel(t: float, beta0: float, beta1: float, beta2: float, lmbda: float) -> float:
    """Calculates model price for maturity t (in years)."""
    if t <= 0:
        t = 1e-6  # Prevent division by zero for spot/same-day maturity
    
    factor1 = (1 - np.exp(-lmbda * t)) / (lmbda * t)
    factor2 = factor1 - np.exp(-lmbda * t)
    return float(beta0 + beta1 * factor1 + beta2 * factor2)

@router.get("/four_months_forwards")
def get_four_months_forwards(valuation_date: str):
    forwards_df = db_manager.get_four_months_forward_prices(valuation_date)
    
    if forwards_df.empty:
        return {"forwards": []}
        
    forwards_list = forwards_df.to_dict(orient="records")
    return {"forwards": forwards_list}

@router.get("/four_months_nelson_forwards", response_model=dict[str, list[ForwardPriceEstimate]])
def get_four_months_nelson_forwards(
    valuation_date: str = Query(..., description="Valuation date in YYYY-MM-DD format"),
):
    # 1. Fetch parameters from nelson_siegel_parameters table
    params_df = db_manager.get_nelson_siegel_parameters(valuation_date)

    if params_df.empty:
        raise HTTPException(
            status_code=404,
            detail=f"No Nelson-Siegel parameters found for valuation date {valuation_date}",
        )

    # Extract parameter values
    param_row = params_df.iloc[0]
    beta0 = param_row["beta0"]
    beta1 = param_row["beta1"]
    beta2 = param_row["beta2"]
    lmbda = param_row["lmbda"]

    # 2. Generate the next 4 monthly forward expiry dates (M+1 to M+4)
    val_dt = pd.to_datetime(valuation_date)
    estimates = []

    for m in range(1, 5):
        # Generate target expiry date (1 to 4 months out)
        expiry_dt = val_dt + pd.DateOffset(months=m)

        # Calculate maturity t in years
        t = (expiry_dt - val_dt).days / 365.25

        # Calculate estimated price using Nelson-Siegel equation
        estimated_price = nelson_siegel(t, beta0, beta1, beta2, lmbda)

        estimates.append(
            ForwardPriceEstimate(
                valuation_date=val_dt.strftime("%Y-%m-%d"),
                expiry_date=expiry_dt.strftime("%Y-%m-%d"),
                tenor=f"M+{m}",
                time_to_maturity_years=round(t, 4),
                estimated_price=round(estimated_price, 4),
            )
        )

    return {"forwards": estimates}