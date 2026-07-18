import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import os

# Set clean styling for the graph
sns.set_theme(style="darkgrid")

st.set_page_config(page_title="Edison Curve Dashboard", layout="centered")

st.title("📈 Edison Forward Curve Dashboard")
st.markdown("Select a valuation target to fetch and plot the truncated forward curve.")

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1/four_months_forwards")

# 1. CREATE A CLEAN SIDE-BY-SIDE MONTH & YEAR PICKER GAUGE
col1, col2 = st.columns(2)

with col1:
    # List the years matching your database historical records
    selected_year = st.selectbox("Select Year:", options=[2020, 2021, 2022, 2023, 2024], index=1) # Defaults to 2024

with col2:
    # Mapping readable month strings directly to their padded numerical values
    month_options = {
        "January": "01", "February": "02", "March": "03", "April": "04",
        "May": "05", "June": "06", "July": "07", "August": "08",
        "September": "09", "October": "10", "November": "11", "December": "12"
    }
    selected_month_name = st.selectbox("Select Month:", options=list(month_options.keys()), index=0) # Defaults to January

# 2. STRIP AWAY THE DAY ENTIRELY AND FORCE IT TO THE 1ST
# This automatically formats perfectly into 'YYYY-MM-01'
valuation_date_str = f"{selected_year}-{month_options[selected_month_name]}-01"

st.info(f"Targeting API Query Parameter: `valuation_date={valuation_date_str}`")

# --- Keep the rest of your original button trigger & plotting script underneath ---
if st.button("Fetch and Plot Curve", type="primary"):
    with st.spinner("Fetching data from API..."):
        try:
            response = requests.get(API_BASE_URL, params={"valuation_date": valuation_date_str})
            
            if response.status_code == 200:
                data = response.json()
                forwards = data.get("forwards", [])
                
                if not forwards:
                    st.warning(f"No forward curve data found for {valuation_date_str} in the database.")
                else:
                    df = pd.DataFrame(forwards)
                    df["expiry_date"] = pd.to_datetime(df["expiry_date"])
                    df = df.sort_values("expiry_date")
                    df["expiry_label"] = df["expiry_date"].dt.strftime("%Y-%m-%d")
                    
                    st.success(f"Successfully loaded {len(df)} contract points!")
                    
                    st.subheader("Raw Curve Grid")
                    st.dataframe(df[["id", "commodity", "expiry_label", "price"]].rename(
                        columns={"expiry_label": "Expiry Date", "price": "Price ($)"}
                    ), use_container_width=True)
                    
                    st.subheader("Forward Curve Visualization")
                    fig, ax = plt.subplots(figsize=(10, 5))
                    ax.plot(df["expiry_label"], df["price"], marker="o", linewidth=2.5, color="#1f77b4", label=f"Curve on {valuation_date_str}")
                    ax.set_title(f"WTI Crude Oil Term Structure ({valuation_date_str})", fontsize=12, fontweight="bold", pad=12)
                    ax.set_xlabel("Contract Expiry Date", fontsize=10)
                    ax.set_ylabel("Price ($/BBL)", fontsize=10)
                    ax.set_ylim(df["price"].min() - 0.5, df["price"].max() + 0.5)
                    ax.legend()
                    st.pyplot(fig)
            else:
                st.error(f"Failed to fetch data. Server responded with code: {response.status_code}")
        except requests.exceptions.ConnectionError:
            st.error("Could not connect to FastAPI server. Make sure it's running on http://localhost:8000")

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