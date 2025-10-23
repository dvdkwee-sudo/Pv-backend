from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import math
from datetime import datetime

app = FastAPI(title="PV Calculator API")

# Enable CORS for Android app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class PVRequest(BaseModel):
    latitude: float
    longitude: float
    system_capacity: float
    panel_efficiency: float = 0.18
    system_losses: float = 0.14

class PVResponse(BaseModel):
    annual_energy: float
    monthly_energy: list
    capacity_factor: float
    psh_annual: float
    roi_period: float
    panel_count: int
    required_area: float
    system_cost: float
    annual_savings: float

@app.get("/")
def read_root():
    return {"message": "PV Calculator API is running!"}

@app.post("/calculate", response_model=PVResponse)
async def calculate_pv(request: PVRequest):
    try:
        # Calculate PSH based on latitude (simplified model)
        psh_annual = calculate_psh(request.latitude, request.longitude)
        
        # Basic energy calculations
        annual_energy = request.system_capacity * psh_annual * 365 * (1 - request.system_losses)
        capacity_factor = (annual_energy / (request.system_capacity * 8760)) * 100
        
        # Monthly energy distribution
        monthly_energy = generate_monthly_energy(annual_energy, request.latitude)
        
        # Financial calculations (in IDR)
        system_cost = request.system_capacity * 18000000  # Rp 18 juta per kWp
        annual_savings = annual_energy * 1500  # Rp 1500 per kWh
        roi_period = system_cost / annual_savings if annual_savings > 0 else 0
        
        # System specifications
        panel_count = int((request.system_capacity * 1000) / 450)  # 450W panels
        required_area = request.system_capacity * 7  # m²
        
        return PVResponse(
            annual_energy=annual_energy,
            monthly_energy=monthly_energy,
            capacity_factor=capacity_factor,
            psh_annual=psh_annual,
            roi_period=roi_period,
            panel_count=panel_count,
            required_area=required_area,
            system_cost=system_cost,
            annual_savings=annual_savings
        )
        
    except Exception as e:
        return {"error": str(e)}

def calculate_psh(lat, lon):
    """Calculate Peak Sun Hours based on latitude and simple model"""
    # Base PSH at equator
    base_psh = 4.5
    
    # Latitude effect (decreases as we move away from equator)
    lat_effect = abs(lat) * 0.02
    
    # Seasonal variation factor
    current_month = datetime.now().month
    seasonal_factor = 1 + 0.1 * math.sin(2 * math.pi * (current_month - 6) / 12)
    
    psh = base_psh - lat_effect
    psh *= seasonal_factor
    
    # Ensure reasonable bounds
    return max(2.0, min(6.0, psh))

def generate_monthly_energy(annual_energy, lat):
    """Generate monthly energy distribution based on latitude (hemisphere)"""
    monthly_factors = []
    
    if lat >= 0:  # Northern hemisphere
        # Summer peak (June-July), winter low (Dec-Jan)
        base_pattern = [0.06, 0.07, 0.08, 0.09, 0.10, 0.12, 
                       0.12, 0.11, 0.10, 0.09, 0.08, 0.07]
    else:  # Southern hemisphere  
        # Summer peak (Dec-Jan), winter low (June-July)
        base_pattern = [0.12, 0.11, 0.10, 0.09, 0.08, 0.07,
                       0.07, 0.08, 0.09, 0.10, 0.11, 0.12]
    
    # Normalize to ensure total = 1.0
    total = sum(base_pattern)
    normalized_pattern = [factor/total for factor in base_pattern]
    
    monthly_energy = [annual_energy * factor for factor in normalized_pattern]
    return monthly_energy

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
