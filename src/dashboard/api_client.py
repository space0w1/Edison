# api_client.py
import os
import requests

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")
API_ACTUAL_URL = f"{API_BASE_URL}/four_months_forwards"
API_NELSON_URL = f"{API_BASE_URL}/four_months_nelson_forwards"
API_BACKTEST_URL = f"{API_BASE_URL}/backtest/nelson_siegel_pnl"

def fetch_market_curves(valuation_date: str):
    """Fetches concurrent forward curve metrics from actual and modeled endpoints."""
    try:
        res_actual = requests.get(API_ACTUAL_URL, params={"valuation_date": valuation_date})
        res_nelson = requests.get(API_NELSON_URL, params={"valuation_date": valuation_date})
        
        return {
            "actual_status": res_actual.status_code,
            "nelson_status": res_nelson.status_code,
            "actual_data": res_actual.json().get("forwards", []) if res_actual.status_code == 200 else [],
            "nelson_data": res_nelson.json().get("forwards", []) if res_nelson.status_code == 200 else []
        }
    except requests.exceptions.ConnectionError:
        raise ConnectionError("Could not connect to backend router. Verify your FastAPI engine is running locally on port 8000.")

def fetch_backtest_pnl(tenor: str, commodity: str = "Crude Oil"):
    """Fetches Nelson-Siegel vs actual backtest results for the given tenor selection."""
    try:
        res = requests.get(API_BACKTEST_URL, params={"tenor": tenor, "commodity": commodity})
        payload = res.json() if res.status_code == 200 else {}

        return {
            "status": res.status_code,
            "trades": payload.get("trades", []),
            "summary": payload.get("summary", []),
        }
    except requests.exceptions.ConnectionError:
        raise ConnectionError("Could not connect to backend router. Verify your FastAPI engine is running locally on port 8000.")