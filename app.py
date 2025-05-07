import sqlite3
import math
from flask import Flask, jsonify, request, g

app = Flask(__name__)

# Database configuration
DATABASE = 'world.sqlite3'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


@app.route('/geoapi/countries', methods=['GET'])
def search_countries():
    query = request.args.get('q', '')
    if not query:
        return jsonify({"countries": []}), 200
    
    # Search for countries that start with the query (case insensitive)
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "SELECT id, name FROM countries WHERE name LIKE ? ORDER BY name LIMIT 10", 
        (f"{query}%",)
    )
    countries = [{"id": row["id"], "name": row["name"]} for row in cursor.fetchall()]
    
    return jsonify({"countries": countries})

@app.route('/geoapi/countries/all', methods=['GET'])
def get_all_countries():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT id, name FROM countries ORDER BY name")
    countries = [{"id": row["id"], "name": row["name"]} for row in cursor.fetchall()]
    return jsonify({"countries": countries})

@app.route('/geoapi/cities', methods=['GET'])
def search_cities():
    country_id = request.args.get('country_id')
    query = request.args.get('q', '')
    
    if not country_id:
        return jsonify({"error": "country_id parameter is required"}), 400
    
    db = get_db()
    cursor = db.cursor()
    
    if query:
        # Search for cities that start with the query in the specified country
        cursor.execute(
            "SELECT id, name, state_code, latitude, longitude FROM cities WHERE country_id = ? AND name LIKE ? ORDER BY name LIMIT 10", 
            (country_id, f"{query}%")
        )
    else:
        # Return all cities in the specified country
        cursor.execute(
            "SELECT id, name, state_code, latitude, longitude FROM cities WHERE country_id = ? ORDER BY name LIMIT 10", 
            (country_id,)
        )
    
    cities = [{"id": row["id"], "name": row["name"], "state_code": row["state_code"], "latitude": row["latitude"], "longitude": row["longitude"]} for row in cursor.fetchall()]
    
    return jsonify({"cities": cities})

@app.route('/geoapi/nearest_city', methods=['GET'])
def find_nearest_city():
    try:
        latitude = float(request.args.get('lat'))
        longitude = float(request.args.get('lon'))
    except (TypeError, ValueError):
        return jsonify({"error": "Valid lat and lon parameters are required"}), 400
    
    # Calculate distance using Haversine formula
    db = get_db()
    cursor = db.cursor()
    
    # Get all cities with their coordinates
    cursor.execute(
        "SELECT id, name, state_code, country_id, latitude, longitude FROM cities WHERE latitude IS NOT NULL AND longitude IS NOT NULL"
    )
    
    nearest_city = None
    min_distance = float('inf')
    
    for row in cursor.fetchall():
        city_lat = row["latitude"]
        city_lon = row["longitude"]
        
        # Haversine formula to calculate distance between two points on Earth
        R = 6371  # Earth radius in kilometers
        
        lat1_rad = math.radians(latitude)
        lon1_rad = math.radians(longitude)
        lat2_rad = math.radians(city_lat)
        lon2_rad = math.radians(city_lon)
        
        dlon = lon2_rad - lon1_rad
        dlat = lat2_rad - lat1_rad
        
        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        distance = R * c
        
        if distance < min_distance:
            min_distance = distance
            nearest_city = {
                "id": row["id"],
                "name": row["name"],
                "state_code": row["state_code"],
                "country_id": row["country_id"],
                "latitude": city_lat,
                "longitude": city_lon,
                "distance_km": round(distance, 2)
            }
    
    if nearest_city:
        return jsonify({"city": nearest_city})
    else:
        return jsonify({"error": "No cities found with valid coordinates"}), 404

if __name__ == '__main__':
    app.run(debug=True)
