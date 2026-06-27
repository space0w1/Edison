import time
import requests
import psycopg2
from psycopg2.extras import execute_values

# --- CONFIGURATION ---
EIA_API_KEY = "NAlaaiRcZCbfC4UlBB4cHoHae1LuCm1Oo1NEsZyZ"
BASE_URL = "https://api.eia.gov/v2/petroleum/pri/spt/data/"

DB_CONFIG = {
    "dbname": "edison",
    "user": "edison",
    "password": "edison_password",
    "host": "localhost",
    "port": 5432
}

def fetch_eia_data():
    offset = 0
    length = 5000  # Pull maximal rows per chunk allowed by EIA
    all_records = []
    
    # Query parameters
    params = {
        "frequency": "daily",
        "data[0]": "value",
        "facets[series][]": "RWTC",
        "sort[0][column]": "period",
        "sort[0][direction]": "desc",
        "length": length,
        "api_key": EIA_API_KEY
    }

    print("Starting data extraction from EIA API...")
    
    while True:
        params["offset"] = offset
        print(f"Fetching rows starting from offset: {offset}...")
        
        response = requests.get(BASE_URL, params=params)
        
        if response.status_code != 200:
            print(f"Error fetching data: {response.text}")
            break
            
        json_data = response.json()
        data_rows = json_data.get("response", {}).get("data", [])
        total_records = int(json_data.get("response", {}).get("total", 0))
        
        if not data_rows:
            break
            
        # Parse out fields to map cleanly into your schema
        for row in data_rows:
            # Map EIA fields into your target columns
            timestamp = row.get("period")  # e.g., "2026-06-22" -> valid timestamp format
            price = float(row.get("value")) if row.get("value") else 0.0
            volume = 0.0  # Note: The raw endpoint payload does not contain volume. Initializing as 0.
            node = row.get("duoarea", "UNKNOWN")  # e.g., "YCUOK"
            market = row.get("product-name", "WTI Crude Oil")  # e.g., "WTI Crude Oil"
            
            all_records.append((timestamp, price, volume, node, market))
            
        # Stop looping if we've processed all records
        offset += len(data_rows)
        if offset >= total_records:
            break
            
        # Polite delay to prevent getting throttled
        time.sleep(0.5)
        
    print(f"Extraction finished. Retrieved {len(all_records)} total rows.")
    return all_records

def load_to_postgres(records):
    if not records:
        print("No records found to insert.")
        return

    insert_query = """
        INSERT INTO spot_prices (timestamp, price, volume, node, market)
        VALUES %s;
    """
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        print("Writing data to PostgreSQL...")
        # execute_values is much faster than running single INSERT statements loop-style
        execute_values(cursor, insert_query, records)
        
        conn.commit()
        print("Ingestion completed successfully!")
        
    except Exception as e:
        print(f"Database error encountered: {e}")
        if conn:
            conn.rollback()
            
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

if __name__ == "__main__":
    extracted_data = fetch_eia_data()
    load_to_postgres(extracted_data)