from datetime import datetime

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

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
        self.engine = create_engine(db_url)
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