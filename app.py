import sqlite3
from flask import Flask, jsonify, request, g

app = Flask(__name__)

# Database configuration
DATABASE = 'countries.db'

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

# Sample data
items = [
    {"id": 1, "name": "Item 1", "description": "Description for item 1"},
    {"id": 2, "name": "Item 2", "description": "Description for item 2"}
]

@app.route('/api/items', methods=['GET'])
def get_items():
    return jsonify({"items": items})

@app.route('/api/items/<int:item_id>', methods=['GET'])
def get_item(item_id):
    item = next((item for item in items if item["id"] == item_id), None)
    if item:
        return jsonify({"item": item})
    return jsonify({"error": "Item not found"}), 404

@app.route('/api/items', methods=['POST'])
def create_item():
    if not request.json or 'name' not in request.json:
        return jsonify({"error": "Invalid request"}), 400
    
    new_item = {
        "id": items[-1]["id"] + 1 if items else 1,
        "name": request.json["name"],
        "description": request.json.get("description", "")
    }
    items.append(new_item)
    return jsonify({"item": new_item}), 201

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

if __name__ == '__main__':
    app.run(debug=True)
