import sqlite3
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


@app.route('/api/countries', methods=['GET'])
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

@app.route('/api/countries/all', methods=['GET'])
def get_all_countries():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT id, name FROM countries ORDER BY name")
    countries = [{"id": row["id"], "name": row["name"]} for row in cursor.fetchall()]
    return jsonify({"countries": countries})

@app.route('/api/cities', methods=['GET'])
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
            "SELECT id, name, state_code FROM cities WHERE country_id = ? AND name LIKE ? ORDER BY name LIMIT 10", 
            (country_id, f"{query}%")
        )
    else:
        # Return all cities in the specified country
        cursor.execute(
            "SELECT id, name, state_code FROM cities WHERE country_id = ? ORDER BY name LIMIT 10", 
            (country_id,)
        )
    
    cities = [{"id": row["id"], "name": row["name"], "state_code": row["state_code"]} for row in cursor.fetchall()]
    
    return jsonify({"cities": cities})

if __name__ == '__main__':
    app.run(debug=True)
