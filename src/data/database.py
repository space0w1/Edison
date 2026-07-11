from datetime import datetime

import os
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from src.config.db_config import LOCAL_DB

# 2. Grab the DATABASE_URL from the YAML env block. If not found, use local fallback.
DATABASE_URL = os.getenv("DATABASE_URL", LOCAL_DB)

class Base:
    pass

class SpotPrice(Base):
    __tablename__ = 'spot_prices'
    
    id: int
    timestamp: datetime
    price: float
    volume : float
    node: str
    market: str

class ForwardPrice(Base):
    __tablename__ = 'forward_prices'
    
    id: int
    valuation_date: datetime
    commodity: str
    expiry_date: datetime
    price: float

class Database:
    def __init__(self, db_url):
        # pool_pre_ping ensures stale connections are automatically dropped/reconnected
        self.engine = create_engine(db_url, pool_pre_ping=True)
        self.Session = sessionmaker(bind=self.engine)

    def insert_spot_price(self, spot_price: SpotPrice):
        with self.Session() as session:
            session.add(spot_price)
            session.commit()

    def insert_forward_price(self, forward_price: ForwardPrice):
        with self.Session() as session:
            session.add(forward_price)
            session.commit()

    def get_spot_prices(self, start_date: datetime, end_date: datetime):
        with self.Session() as session:
            query = text("""
                SELECT * FROM spot_prices
                WHERE timestamp BETWEEN :start_date AND :end_date
            """)
            result = session.execute(query, {'start_date': start_date, 'end_date': end_date})
            return pd.DataFrame(result.fetchall(), columns=result.keys())

    def get_forward_prices(self, valuation_date: datetime):
        with self.Session() as session:
            query = text("""
                SELECT * FROM forward_prices
                WHERE valuation_date = :valuation_date
            """)
            result = session.execute(query, {'valuation_date': valuation_date})
            return pd.DataFrame(result.fetchall(), columns=result.keys())
        
    def get_four_months_forward_prices(self, valuation_date: datetime):
        with self.Session() as session:
            query = text("""
                SELECT * FROM forward_prices
                WHERE valuation_date = :valuation_date AND
                expiry_date BETWEEN :valuation_date AND :four_months_later
            """)
                    # 1. Convert the string to a proper datetime object first!
            val_date_dt = pd.to_datetime(valuation_date)
            
            # 2. Use the datetime object for your date math
            four_months_later = val_date_dt + pd.DateOffset(months=4)
            result = session.execute(query, {'valuation_date': val_date_dt, 'four_months_later': four_months_later})
            return pd.DataFrame(result.fetchall(), columns=result.keys())
        
db_manager = Database(DATABASE_URL)