import sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from sqlalchemy import create_engine, text

# Ensure project root is in sys.path
sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.config.db_config import LOCAL_DB


def nelson_siegel(t, beta0, beta1, beta2, lmbda):
    """Calculates Nelson-Siegel model yield/price curve."""
    # Prevent division by zero for spot contracts
    t = np.where(t == 0, 1e-6, t)
    factor1 = (1 - np.exp(-lmbda * t)) / (lmbda * t)
    factor2 = factor1 - np.exp(-lmbda * t)
    return beta0 + beta1 * factor1 + beta2 * factor2


def loss_func(params, t, y):
    """Sum of squared residuals between actual prices and Nelson-Siegel model."""
    beta0, beta1, beta2, lmbda = params
    y_pred = nelson_siegel(t, beta0, beta1, beta2, lmbda)
    return np.sum((y - y_pred) ** 2)


def fit_nelson_siegel(curve_df):
    """Fits Nelson-Siegel parameters for a single valuation curve."""
    # Compute time to maturity in years as a numpy array
    t = ((curve_df["expiry_date"] - curve_df["valuation_date"]).dt.days / 365.25).to_numpy()
    y = curve_df["price"].to_numpy()

    # Initial guesses: [beta0, beta1, beta2, lmbda]
    init_params = [y.mean(), 0.0, 0.0, 1.0]

    # Parameter bounds
    bounds = [
        (None, None),    # beta0 (Level)
        (None, None),    # beta1 (Slope)
        (None, None),    # beta2 (Curvature)
        (0.0001, 10.0),  # lmbda (Decay)
    ]

    res = minimize(
        loss_func,
        init_params,
        args=(t, y),
        method="L-BFGS-B",
        bounds=bounds,
    )

    if res.success:
        beta0, beta1, beta2, lmbda = res.x
        ssr_loss = res.fun
        return beta0, beta1, beta2, lmbda, ssr_loss
    else:
        return None, None, None, None, None


def main():
    engine = create_engine(LOCAL_DB)

    # 1. Fetch raw price data
    query = """
        SELECT id, valuation_date, commodity, expiry_date, price
        FROM forward_prices
        ORDER BY valuation_date ASC;
    """
    df = pd.read_sql(query, engine)
    print(f"Fetched {len(df)} rows from forward_prices.")

    if df.empty:
        print("No data found in forward_prices. Aborting.")
        return

    # Convert date columns to datetime
    df["valuation_date"] = pd.to_datetime(df["valuation_date"])
    df["expiry_date"] = pd.to_datetime(df["expiry_date"])

    records = []

    # 2. Group by commodity and valuation_date directly
    grouped = df.groupby(["commodity", "valuation_date"])
    print(f"Processing {len(grouped)} valuation date groups...")

    for (commodity, val_date), curve_df in grouped:
        if len(curve_df) < 4:
            continue

        b0, b1, b2, lmbda, loss = fit_nelson_siegel(curve_df)

        if b0 is not None:
            records.append(
                {
                    "valuation_date": val_date,
                    "commodity": commodity,
                    "beta0": float(b0),
                    "beta1": float(b1),
                    "beta2": float(b2),
                    "lmbda": float(lmbda),
                    "ssr_loss": float(loss),
                }
            )

    if not records:
        print("No valid parameter estimations were produced.")
        return

    results_df = pd.DataFrame(records)

    # 3. Upsert parameter results into PostgreSQL
    upsert_sql = text(
        """
        INSERT INTO nelson_siegel_parameters 
            (valuation_date, commodity, beta0, beta1, beta2, lmbda, ssr_loss)
        VALUES 
            (:valuation_date, :commodity, :beta0, :beta1, :beta2, :lmbda, :ssr_loss)
        ON CONFLICT (valuation_date, commodity) 
        DO UPDATE SET
            beta0 = EXCLUDED.beta0,
            beta1 = EXCLUDED.beta1,
            beta2 = EXCLUDED.beta2,
            lmbda = EXCLUDED.lmbda,
            ssr_loss = EXCLUDED.ssr_loss,
            created_at = CURRENT_TIMESTAMP;
        """
    )

    with engine.begin() as conn:
        conn.execute(upsert_sql, results_df.to_dict(orient="records"))

    print(f"Successfully written {len(results_df)} records to nelson_siegel_parameters.")


if __name__ == "__main__":
    main()