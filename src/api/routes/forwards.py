from fastapi import APIRouter
from pydantic import BaseModel
from  src.data.database import db_manager

router = APIRouter()

class forward_prices(BaseModel):
    valuation_date: str
    commodity: str
    expiry_date: str
    price: float

@router.get("/four_months_forwards")
def get_four_months_forwards(valuation_date: str):
    forwards_df = db_manager.get_four_months_forward_prices(valuation_date)
    
    if forwards_df.empty:
        return {"forwards": []}
        
    forwards_list = forwards_df.to_dict(orient="records")
    return {"forwards": forwards_list}