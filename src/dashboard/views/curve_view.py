# views/curve_view.py
import streamlit as st
import seaborn as sns
from api_client import fetch_market_curves
from data_utils import compile_asymmetric_curves, generate_comparison_plot

# Set clean styling for the graph
sns.set_theme(style="darkgrid")

st.title("📈 Forward Curve Dashboard")
st.markdown("Select a valuation target to compare actual vs. Nelson-Siegel estimated curves.")

# 1. UI Dropdown Layout Components
col1, col2 = st.columns(2)

with col1:
    selected_year = st.selectbox("Select Year:", options=[2020, 2021, 2022, 2023, 2024], index=1)

with col2:
    month_options = {
        "January": "01", "February": "02", "March": "03", "April": "04",
        "May": "05", "June": "06", "July": "07", "August": "08",
        "September": "09", "October": "10", "November": "11", "December": "12"
    }
    selected_month_name = st.selectbox("Select Month:", options=list(month_options.keys()), index=0)

valuation_date_str = f"{selected_year}-{month_options[selected_month_name]}-01"
st.info(f"Targeting Parameters: `valuation_date={valuation_date_str}`")

# 2. Network Synchronisation & Execution Trigger
if st.button("Fetch and Compare Curves", type="primary"):
    with st.spinner("Synchronizing asymmetric pipelines from Edison API..."):
        try:
            payload = fetch_market_curves(valuation_date_str)

            # Catch structural HTTP connection drop-outs early
            if payload["actual_status"] != 200 or payload["nelson_status"] != 200:
                st.error(f"Failed API handshake. Actual Route: {payload['actual_status']} | Nelson Route: {payload['nelson_status']}")
                st.stop()

            if not payload["nelson_data"]:
                st.warning(f"No modeled historical calibrations found matching target date: {valuation_date_str}")
                st.stop()

            # Align inputs through the asymmetric processing engine
            df_merged = compile_asymmetric_curves(payload["actual_data"], payload["nelson_data"])
            st.success(f"Successfully compiled curve model array mapping horizon parameters!")

            # Display conditional status notice if the fourth node is isolated
            if df_merged["price"].isna().any():
                missing_labels = df_merged[df_merged["price"].isna()]["expiry_label"].tolist()
                st.warning(f"⚠️ Market prices missing for future dates: {', '.join(missing_labels)}. Displaying Nelson-Siegel extrapolation path.")

            # --- Dataframe View ---
            st.subheader("Raw Curve Grid Comparison")
            # Present NaN entries elegantly using Streamlit's built-in empty field rendering
            display_df = df_merged[["commodity", "expiry_label", "price", "estimated_price"]].rename(
                columns={
                    "expiry_label": "Expiry Date",
                    "price": "Actual Price ($)",
                    "estimated_price": "NS Estimated Price ($)"
                }
            )
            st.dataframe(display_df, use_container_width=True)

            # --- Graph View ---
            st.subheader("Forward Curve Comparison Model")
            fig = generate_comparison_plot(df_merged, valuation_date_str)
            st.pyplot(fig)

        except ConnectionError as ce:
            st.error(str(ce))

# --- Footnote Section ---
st.markdown("---")
st.markdown(
    """
    <div style="text-align: center; color: gray; font-size: 0.8em;">
        Data provided by Edison API | Built by space0w1
    </div>
    """,
    unsafe_allow_html=True
)
