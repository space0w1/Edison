import psycopg2
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

sns.set_theme(style="darkgrid")

DB_CONFIG = {
    "dbname": "edison",
    "user": "edison",
    "password": "edison_password",
    "host": "localhost",
    "port": 5432
}

def plot_spot_vs_futures():
    # 1. Pull daily spot prices
    spot_query = """
        SELECT timestamp::date AS date, price AS spot_price
        FROM spot_prices 
        WHERE timestamp >= '2010-01-01' AND timestamp <= '2024-01-01'
        ORDER BY date ASC;
    """
    
    # 2. Pull monthly futures prices (filtering for Contract 1 Crude Oil to match spot closely)
    futures_query = """
        SELECT valuation_date::date AS date, price AS futures_price
        FROM forward_prices
        WHERE commodity = 'Crude Oil'
          AND valuation_date >= '2010-01-01' 
          AND valuation_date <= '2024-01-01'
          AND expiry_date = valuation_date  -- This isolates "Contract 1" (Prompt Month)
        ORDER BY date ASC;
    """
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        
        # Read datasets into dataframes
        df_spot = pd.read_sql_query(spot_query, conn)
        df_fut = pd.read_sql_query(futures_query, conn)
        
        # Ensure correct datetime formatting and index
        df_spot['date'] = pd.to_datetime(df_spot['date'])
        df_fut['date'] = pd.to_datetime(df_fut['date'])
        
        df_spot.set_index('date', inplace=True)
        df_fut.set_index('date', inplace=True)
        
        # --- PLOTTING ---
        plt.figure(figsize=(14, 7))
        
        # Plot continuous daily spot price
        plt.plot(df_spot.index, df_spot['spot_price'], 
                 color='tab:blue', alpha=0.6, linewidth=1.2, label='WTI Spot Price (Daily)')
        
        # Plot monthly futures step/line
        plt.plot(df_fut.index, df_fut['futures_price'], 
                 color='tab:orange', linestyle='--', linewidth=1.8, marker='o', markersize=4, label='WTI Front-Month Future (Monthly)')
        
        # Formatting
        plt.title('WTI Crude Oil: Spot Price vs. Front-Month Futures (2010 - 2024)', fontsize=14, fontweight='bold', pad=15)
        plt.xlabel('Year', fontsize=12)
        plt.ylabel('Price ($/BBL)', fontsize=12)
        plt.legend(fontsize=11, loc='upper right')
        
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.show()
        
    except Exception as e:
        print(f"Error generating comparative plot: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == "__main__":
    plot_spot_vs_futures()