import json, os, math
from geopy.distance import geodesic

def load_aircraft_emissions(filepath=None):
    if filepath is None:
        filepath = os.path.join("base_data", "aircraft_emissions.json")
    with open(filepath, "r") as f:
        src = json.load(f)
    fc = {k: dict(v) for k, v in src.get("flight_categories", {}).items()}
    ac = {k: {kk: float(vv) for kk, vv in v.items()} for k, v in src.get("aircraft", {}).items()}
    return fc, ac

def load_train_emissions(filepath=None):
    if filepath is None:
        filepath = os.path.join("base_data", "train_emissions.json")
    with open(filepath, "r") as f:
        return json.load(f)

TRAIN_FACTORS = load_train_emissions()
FLIGHT_CATEGORIES, AIRCRAFT_CATEGORY_CO2 = load_aircraft_emissions()

# Constants for train energy consumption and emissions
ELECTRIC_TRAIN_KWH_PER_KM = 0.04  # kWh per passenger-km for electric trains
DIESEL_TRAIN_LITERS_PER_KM = 0.015  # liters per passenger-km for diesel trains
DIESEL_CO2_KG_PER_LITER = 2.65  # kg CO2 per liter of diesel

EMISSION_FACTORS = {
    'bus': {'construction': 4.42, 'fuel': 25.0, 'infrastructure': 0.7},
    'car': {'construction': 25.6, 'fuel': 192.0, 'infrastructure': 0.7, 'additional_passenger_factor': 0.04},
    'air': {
        'short': {'base_co2_per_km': 0.300},
        'medium': {'base_co2_per_km': 0.200},
        'long': {'base_co2_per_km': 0.167},
        'non_co2_factor': 1.7,
        'detour_factor': 1.076,
    },
    'ferry': {'combustion': 80.0, 'services': 30.0, 'construction': 11.0},
    'cycle': {'construction': 5.0, 'human_fuel': 16.0},
    'walk': {'human_fuel': 16.0},
    'metro': 'train',
    'tram': 'train',
    'aerialway': 'train'
}

def calculate_great_circle_distance(p1, p2):
    return geodesic(p1, p2).meters

def calculate_path_distance(path):
    if len(path) < 2: return 0
    return sum(calculate_great_circle_distance(path[i], path[i+1]) for i in range(len(path)-1))

def get_flight_category(distance_km, categories=FLIGHT_CATEGORIES):
    cand = []
    for name, b in categories.items():
        dmin = b.get("distance_km_min", float("-inf"))
        dmax = b.get("distance_km_max", float("inf"))
        if dmin <= distance_km < dmax:
            span = (dmax - dmin) if math.isfinite(dmax) and math.isfinite(dmin) else float("inf")
            cand.append((span, dmin, name))
    return min(cand)[2] if cand else None

def get_aircraft_co2_value(aircraft_code, distance_km):
    per_cat = AIRCRAFT_CATEGORY_CO2.get(aircraft_code)
    if not per_cat: return None
    cat = get_flight_category(distance_km)
    return per_cat.get(cat) if cat and cat in per_cat else per_cat.get("all")

def get_trip_distance_km(trip, path, trip_type):
    if trip_type == 'air' and len(path) == 2:
        m = calculate_great_circle_distance(path[0], path[1])
        return (m/1000) * EMISSION_FACTORS['air']['detour_factor']
    if trip_type == 'air' and len(path) > 2:
        return calculate_path_distance(path) / 1000
    m = trip.get('trip_length', 0) or (calculate_path_distance(path) if path else 0)
    return m / 1000

def calculate_air_emissions(distance_km, path_points, aircraft_code=''):
    f = EMISSION_FACTORS['air']
    v = get_aircraft_co2_value(aircraft_code, distance_km)
    if v is not None:
        return distance_km * v * f['non_co2_factor']
    cat = 'short' if distance_km < 1000 else ('medium' if distance_km < 3500 else 'long')
    return distance_km * f[cat]['base_co2_per_km'] * f['non_co2_factor']

def split_km_for_country(cc, value_m):
    """Split distance into electric and diesel kilometers based on country's diesel share"""
    if isinstance(value_m, dict):
        # If already split, convert from meters to km
        e_km = (value_m.get('electric_m', 0) or 0) / 1000
        d_km = (value_m.get('diesel_m', 0) or 0) / 1000
        return e_km, d_km
    
    # Convert total meters to km
    total_km = (value_m or 0) / 1000
    
    # Get diesel share for this country (default if not found)
    diesel_share = TRAIN_FACTORS.get(cc, TRAIN_FACTORS['default'])['diesel_share']
    
    # Calculate diesel and electric km
    diesel_km = total_km * diesel_share
    electric_km = total_km - diesel_km
    
    return electric_km, diesel_km

def calculate_train_emissions(distance_km, countries, force_electric=False):
    """
    Calculate train CO2 emissions in kg CO2e
    
    Args:
        distance_km: Total distance (not used when countries dict provided)
        countries: Dict of country codes and distances, or JSON string
        force_electric: If True, treat all trains as electric
    
    Returns:
        float: Total CO2 emissions in kg CO2e
    """
    # Handle case where no countries specified - use default values
    if not countries:
        factors = TRAIN_FACTORS['default']
        electric_km = distance_km
        diesel_km = 0 if force_electric else distance_km * factors['diesel_share']
        electric_km = distance_km - diesel_km if not force_electric else distance_km
        
        # Calculate emissions
        electric_emissions = electric_km * ELECTRIC_TRAIN_KWH_PER_KM * factors['grid_intensity_g_per_kwh'] / 1000
        diesel_emissions = diesel_km * DIESEL_TRAIN_LITERS_PER_KM * DIESEL_CO2_KG_PER_LITER
        
        return electric_emissions + diesel_emissions
    
    # Parse countries if it's a JSON string
    if isinstance(countries, str):
        try:
            countries = json.loads(countries)
        except:
            countries = {}
    
    total_emissions = 0.0
    
    # Process each country
    for country_code, distance_value in countries.items():
        # Get country-specific factors (or default)
        factors = TRAIN_FACTORS.get(country_code, TRAIN_FACTORS['default'])
        
        # Split into electric and diesel kilometers
        electric_km, diesel_km = split_km_for_country(country_code, distance_value)
        
        # Force all to electric if requested
        if force_electric:
            electric_km += diesel_km
            diesel_km = 0
        
        # Calculate electric train emissions (grid electricity)
        electric_emissions = electric_km * ELECTRIC_TRAIN_KWH_PER_KM * factors['grid_intensity_g_per_kwh'] / 1000
        
        # Calculate diesel train emissions (direct fuel combustion)
        diesel_emissions = diesel_km * DIESEL_TRAIN_LITERS_PER_KM * DIESEL_CO2_KG_PER_LITER
        
        total_emissions += electric_emissions + diesel_emissions
    
    return total_emissions

def calculate_bus_emissions(distance_km):
    g = EMISSION_FACTORS['bus']
    return distance_km * (g['construction'] + g['fuel'] + g['infrastructure']) / 1000

def calculate_car_emissions(distance_km, passengers=1):
    g = EMISSION_FACTORS['car']
    total = distance_km * (g['construction'] + g['fuel'] + g['infrastructure'])
    if passengers > 1:
        total += distance_km * g['fuel'] * g['additional_passenger_factor'] * (passengers - 1)
    return (total / passengers) / 1000

def calculate_ferry_emissions(distance_km):
    g = EMISSION_FACTORS['ferry']
    return distance_km * (g['combustion'] + g['services'] + g['construction']) / 1000

def calculate_cycle_emissions(distance_km):
    g = EMISSION_FACTORS['cycle']
    return distance_km * (g['construction'] + g['human_fuel']) / 1000

def calculate_walk_emissions(distance_km):
    g = EMISSION_FACTORS['walk']
    return distance_km * g['human_fuel'] / 1000

def calculate_carbon_footprint_for_trip(trip, path):
    t = trip.get('type', '').lower()
    if t not in ['train','bus','air','helicopter','ferry','cycle','walk','metro','tram','aerialway','car']:
        return 0
    if t == 'helicopter': t = 'air'
    distance_km = get_trip_distance_km(trip, path, t)
    if distance_km == 0: return 0
    if t == 'air':
        return calculate_air_emissions(distance_km, len(path), trip.get('material_type',''))
    if t in ['train']:
        return calculate_train_emissions(distance_km, trip.get('countries', {}), force_electric=False)
    if t in ['metro','tram','aerialway']:
        return calculate_train_emissions(distance_km, trip.get('countries', {}), force_electric=True)
    if t == 'bus':
        return calculate_bus_emissions(distance_km)
    if t == 'car':
        return calculate_car_emissions(distance_km, trip.get('passengers', 1))
    if t == 'ferry':
        return calculate_ferry_emissions(distance_km)
    if t == 'cycle':
        return calculate_cycle_emissions(distance_km)
    if t == 'walk':
        return calculate_walk_emissions(distance_km)
    return 0