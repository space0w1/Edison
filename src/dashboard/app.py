# app.py
import os

import streamlit as st

st.set_page_config(page_title="Edison", page_icon="📈", layout="centered")

LOGO_PATH = os.path.join(os.path.dirname(__file__), "assets", "logo.png")
st.logo(LOGO_PATH, size="large")

curve_page = st.Page("views/curve_view.py", title="Forward Curves", icon="📈", default=True)
backtest_page = st.Page("views/backtest_view.py", title="Backtest", icon="🧪")

pg = st.navigation([curve_page, backtest_page])
pg.run()
