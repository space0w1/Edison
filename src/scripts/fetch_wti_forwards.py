import time
import re
from datetime import datetime
import requests
import psycopg2
from psycopg2.extras import execute_values
from dateutil.relativedelta import relativedelta

# --- CONFIGURATION ---
EIA_API_KEY = "NAlaaiRcZCbfC4UlBB4cHoHae1LuCm1Oo1NEsZyZ"
BASE_URL = "https://api.eia.gov/v2/petroleum/pri/fut/data/"

DB_CONFIG = {
    "dbname": "edison",
    "user": "edison",
    "password": "edison_password",
    "host": "localhost",
    "port": 5432
}

def parse_dates(period_str, process_name):
    """
    Transforms '2024-04' into a proper valuation date, and extracts the 
    contract number from 'Future Contract 2' to calculate the expiry date.
    """
    # Valuation date defaults to the 1st of the given month
    val_date = datetime.strptime(f"{period_str}-01", "%Y-%m-%d")
    
    # Extract contract integer from process_name string (e.g., "Future Contract 4" -> 4)
    contract_match = re.search(r'\d+', process_name)
    contract_num = int(contract_match.group()) if contract_match else 1
    
    # Compute expiry date based on contract number offset
    # Contract 1 -> expires valuation month, Contract 2 -> valuation month + 1 month, etc.
    expiry_date = val_date + relativedelta(months=(contract_num - 1))
    return val_date, expiry_date

def fetch_and_ingest_wti_curve():
    offset = 0
    length = 5000  # Pull maximal rows per chunk allowed by EIA
    
    params = {
        "frequency": "monthly",
        "data[0]": "value",
        "start": "2000-01",
        "end": "2024-04",
        "sort[0][column]": "period",
        "sort[0][direction]": "desc",
        "length": length,
        "api_key": EIA_API_KEY
    }

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        print("Connected to PostgreSQL database successfully.")
        
        insert_query = """
            INSERT INTO forward_prices (valuation_date, commodity, expiry_date, price)
            VALUES %s;
        """
        
        total_filtered_rows = 0
        
        while True:
            params["offset"] = offset
            print(f"Requesting data chunk from EIA starting at offset {offset}...")
            
            response = requests.get(BASE_URL, params=params)
            if response.status_code != 200:
                print(f"API Error encountered: {response.text}")
                break
                
            json_data = response.json()
            data_rows = json_data.get("response", {}).get("data", [])
            total_records = int(json_data.get("response", {}).get("total", 0))
            
            if not data_rows:
                print("No more data received from API.")
                break
                
            chunk_records = []
            for row in data_rows:
                commodity = row.get("product-name")
                
                # --- WTI CURVE FILTER ---
                # Exclude refined products (Heating Oil, Gasoline) to isolate WTI Crude Oil
                if commodity != "Crude Oil":
                    continue
                
                val_str = row.get("value")
                if not val_str or val_str == ".":
                    continue  # Filter out null records
                
                period = row.get("period")          # e.g., "2024-04"
                process = row.get("process-name")   # e.g., "Future Contract 2"
                
                val_date, exp_date = parse_dates(period, process)
                price = float(val_str)
                
                chunk_records.append((val_date, commodity, exp_date, price))
            
            # Batch write WTI filtered rows directly to database
            if chunk_records:
                execute_values(cursor, insert_query, chunk_records)
                conn.commit()
                total_filtered_rows += len(chunk_records)
                print(f"Successfully processed and saved {len(chunk_records)} WTI rows from this chunk.")
            
            offset += len(data_rows)
            if offset >= total_records:
                print(f"All chunks read. Ingested a total of {total_filtered_rows} pure WTI records.")
                break
                
            time.sleep(0.5) # Polite API cooldown
            
    except Exception as e:
        print(f"Ingestion process failed: {e}")
        if 'conn' in locals() and conn:
            conn.rollback()
    finally:
        if 'cursor' in locals() and cursor: cursor.close()
        if 'conn' in locals() and conn: conn.close()
        print("Database connections cleanly closed.")

if __name__ == "__main__":
    fetch_and_ingest_wti_curve()