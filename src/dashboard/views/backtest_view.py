# views/backtest_view.py
import pandas as pd
import seaborn as sns
import streamlit as st

from api_client import fetch_backtest_pnl
from data_utils import generate_pnl_plot

sns.set_theme(style="darkgrid")

st.title("🧪 Nelson-Siegel Backtest")
st.markdown(
    "Backtests a simple signal strategy: **buy** the forward when the Nelson-Siegel model price "
    "is below the actual market price, **sell** when it's above. The position is closed one month "
    "later on the same contract with the opposite trade. Only the M+2 and M+3 contracts are "
    "considered — anything closer to expiry is skipped."
)

tenor_options = {
    "M+2 only": "M2",
    "M+3 only": "M3",
    "M+2 and M+3": "both",
}
selected_label = st.selectbox("Select tenor(s) to backtest:", options=list(tenor_options.keys()), index=2)
tenor_param = tenor_options[selected_label]

if st.button("Run Backtest", type="primary"):
    with st.spinner("Running backtest against historical curves..."):
        try:
            result = fetch_backtest_pnl(tenor_param)

            if result["status"] != 200:
                st.error(f"Failed to run backtest (status {result['status']}). Check that the backend has enough historical data.")
                st.stop()

            trades = result["trades"]
            summary = result["summary"]

            if not trades:
                st.warning("No completed trades found for the selected tenor(s).")
                st.stop()

            trades_df = pd.DataFrame(trades)
            trades_df["valuation_date"] = pd.to_datetime(trades_df["valuation_date"])
            trades_df = trades_df.sort_values(["tenor", "valuation_date"])
            trades_df["cumulative_pnl"] = trades_df.groupby("tenor")["pnl"].cumsum()

            # --- Summary Metrics ---
            st.subheader("Summary")
            summary_df = pd.DataFrame(summary)
            cols = st.columns(len(summary_df))
            for col, (_, row) in zip(cols, summary_df.iterrows()):
                col.metric(
                    label=f"{row['tenor']} Total PnL",
                    value=f"${row['total_pnl']:.2f}",
                    delta=f"{row['win_rate']:.1f}% win rate | {row['trade_count']} trades",
                )

            # --- PnL Chart ---
            st.subheader("Cumulative PnL Over Time")
            fig = generate_pnl_plot(trades_df)
            st.pyplot(fig)

            # --- Trade Log ---
            st.subheader("Trade Log")
            display_df = trades_df[[
                "tenor", "valuation_date", "expiry_date", "ns_price", "entry_price",
                "signal", "exit_valuation_date", "exit_price", "pnl"
            ]].rename(columns={
                "tenor": "Tenor",
                "valuation_date": "Entry Date",
                "expiry_date": "Contract Expiry",
                "ns_price": "NS Model Price ($)",
                "entry_price": "Entry Price ($)",
                "signal": "Signal",
                "exit_valuation_date": "Exit Date",
                "exit_price": "Exit Price ($)",
                "pnl": "PnL ($)",
            })
            st.dataframe(display_df, use_container_width=True)

        except ConnectionError as ce:
            st.error(str(ce))
