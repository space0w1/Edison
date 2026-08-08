# data_utils.py
import pandas as pd
import matplotlib.pyplot as plt

def compile_asymmetric_curves(actual_list: list, nelson_list: list) -> pd.DataFrame:
    """Merges sets via left-join to support 3 actual periods + 1 predictive period."""
    if not nelson_list:
        return pd.DataFrame()
        
    df_nelson = pd.DataFrame(nelson_list)
    df_nelson["expiry_date"] = pd.to_datetime(df_nelson["expiry_date"])
    
    if actual_list:
        df_actual = pd.DataFrame(actual_list)
        df_actual["expiry_date"] = pd.to_datetime(df_actual["expiry_date"])
        df_actual["valuation_date"] = pd.to_datetime(df_actual["valuation_date"])
        
        # CRITICAL FIX: Strip out the row where expiry matches the valuation baseline date
        df_actual = df_actual[df_actual["expiry_date"] > df_actual["valuation_date"]]
        
        # Now head(3) safely takes M+1 (April), M+2 (May), and M+3 (June)
        df_actual = df_actual.sort_values("expiry_date").head(3)
    else:
        df_actual = pd.DataFrame(columns=["expiry_date", "commodity", "price"])
        df_actual["expiry_date"] = pd.to_datetime(df_actual["expiry_date"])

    # Left join using Nelson-Siegel tracking array as master timeline
    df_merged = pd.merge(
        df_nelson[["expiry_date", "estimated_price", "tenor"]],
        df_actual[["expiry_date", "commodity", "price"]],
        on="expiry_date",
        how="left"
    ).sort_values("expiry_date")
    
    df_merged["expiry_label"] = df_merged["expiry_date"].dt.strftime("%Y-%m-%d")
    df_merged["commodity"] = df_merged["commodity"].bfill().ffill()
    
    return df_merged

def generate_comparison_plot(df: pd.DataFrame, valuation_date_str: str):
    """Plots a continuous estimated curve over a truncated actual market path."""
    fig, ax = plt.subplots(figsize=(10, 5))
    
    # Matplotlib ignores NaN points, leaving a clean terminal break after month 3
    ax.plot(
        df["expiry_label"], df["price"], 
        marker="o", linewidth=2.5, color="#1f77b4", 
        label="Actual Market Curve (M+1 to M+3)"
    )
    
    # Plots the continuous Nelson-Siegel line across all 4 periods
    ax.plot(
        df["expiry_label"], df["estimated_price"], 
        marker="x", linewidth=2.0, color="#d62728", linestyle="--", 
        label="Nelson-Siegel Model Horizon (M+1 to M+4)"
    )
    
    ax.set_title(f"WTI Crude Oil Term Structure Model Comparison ({valuation_date_str})", fontsize=12, fontweight="bold", pad=12)
    ax.set_xlabel("Contract Expiry Date", fontsize=10)
    ax.set_ylabel("Price ($/BBL)", fontsize=10)
    
    # Clean calculations for boundary thresholds filtering out missing components
    valid_actuals = df["price"].dropna()
    min_val = min(valid_actuals.min() if not valid_actuals.empty else df["estimated_price"].min(), df["estimated_price"].min())
    max_val = max(valid_actuals.max() if not valid_actuals.empty else df["estimated_price"].max(), df["estimated_price"].max())
    ax.set_ylim(min_val - 0.5, max_val + 0.5)
    
    ax.legend(loc="best")
    return fig
