import math
import sqlite3

from flask import Flask, g, jsonify, request

app = Flask(__name__)

# Database configuration
DATABASE = 'world.sqlite3'

CITY_COLUMNS = """
    c.id, c.name, c.state_code, s.name AS state, c.country_id,
    co.name AS country, co.iso2 AS country_code, c.latitude, c.longitude
"""
CITY_FROM = """
    FROM cities c
    JOIN countries co ON co.id = c.country_id
    LEFT JOIN states s ON s.id = c.state_id
"""


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


def city_dict(row):
    """Shape a joined city row for JSON. `state` and `country` are display names."""
    return {
        "id": row["id"],
        "name": row["name"].strip(),
        "state_code": row["state_code"],
        "state": row["state"].strip() if row["state"] else None,
        "country_id": row["country_id"],
        "country": row["country"],
        "country_code": row["country_code"],
        "latitude": row["latitude"],
        "longitude": row["longitude"],
    }


def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in kilometers
    lat1_rad, lon1_rad = math.radians(lat1), math.radians(lon1)
    lat2_rad, lon2_rad = math.radians(lat2), math.radians(lon2)
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


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


@app.route('/geoapi/search', methods=['GET'])
def search_places():
    """
    One-box place search for the web app.

    Query parameters:
    - q: free text, "City" or "City, Region" where Region is a state code or
         name, or a country code or name (e.g. "Paris, TX", "Paris, France").
    - cc: optional ISO2 country code to rank first when names are ambiguous
          (the client passes the user's locale or current country).

    Results are ordered: national capitals, exact name match, the preferred
    country, shorter names, then country and state alphabetically.
    """
    raw = request.args.get('q', '').strip()
    cc = request.args.get('cc', '').strip().upper()[:2]
    if len(raw) < 2:
        return jsonify({"results": []})

    parts = [p.strip() for p in raw.split(',', 1)]
    name = parts[0]
    region = parts[1] if len(parts) > 1 else ''

    where = ["c.name LIKE ?"]
    params = [f"{name}%"]
    if region:
        where.append(
            "(c.state_code = ? OR s.name LIKE ? OR co.iso2 = ? OR co.iso3 = ? OR co.name LIKE ?)"
        )
        params += [region.upper(), f"{region}%", region.upper(), region.upper(), f"{region}%"]

    sql = f"""
        SELECT {CITY_COLUMNS}
        {CITY_FROM}
        WHERE {' AND '.join(where)}
        ORDER BY (trim(c.name) = co.capital) DESC,
                 (trim(c.name) = ? COLLATE NOCASE) DESC,
                 (co.iso2 = ?) DESC,
                 length(c.name), co.name, s.name
        LIMIT 10
    """
    params += [name, cc]

    cursor = get_db().cursor()
    cursor.execute(sql, params)
    return jsonify({"results": [city_dict(row) for row in cursor.fetchall()]})


@app.route('/geoapi/nearest_city', methods=['GET'])
def find_nearest_city():
    try:
        latitude = float(request.args.get('lat'))
        longitude = float(request.args.get('lon'))
    except (TypeError, ValueError):
        return jsonify({"error": "Valid lat and lon parameters are required"}), 400

    db = get_db()
    cursor = db.cursor()

    # Look in a widening box around the point so the Haversine pass only
    # touches nearby rows instead of every city in the table.
    for half_deg in (0.5, 2.0, 8.0, 180.0):
        lon_half = min(180.0, half_deg / max(0.1, math.cos(math.radians(latitude))))
        cursor.execute(
            f"""
            SELECT {CITY_COLUMNS}
            {CITY_FROM}
            WHERE c.latitude BETWEEN ? AND ? AND c.longitude BETWEEN ? AND ?
            """,
            (latitude - half_deg, latitude + half_deg, longitude - lon_half, longitude + lon_half)
        )
        rows = cursor.fetchall()
        if rows:
            break

    nearest_city = None
    min_distance = float('inf')
    for row in rows:
        distance = haversine_km(latitude, longitude, row["latitude"], row["longitude"])
        if distance < min_distance:
            min_distance = distance
            nearest_city = city_dict(row)
            nearest_city["distance_km"] = round(distance, 2)

    if nearest_city:
        return jsonify({"city": nearest_city})
    else:
        return jsonify({"error": "No cities found with valid coordinates"}), 404


if __name__ == '__main__':
    app.run(debug=True)
