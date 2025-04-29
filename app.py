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

if __name__ == '__main__':
    # Initialize the database if it doesn't exist
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        # Check if countries table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='countries'")
        if not cursor.fetchone():
            # Create countries table and add some sample data
            cursor.execute('''
                CREATE TABLE countries (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL
                )
            ''')
            sample_countries = [
                "Afghanistan", "Albania", "Algeria", "Andorra", "Angola", 
                "Antigua and Barbuda", "Argentina", "Armenia", "Australia", 
                "Austria", "Azerbaijan", "Bahamas", "Bahrain", "Bangladesh", 
                "Barbados", "Belarus", "Belgium", "Belize", "Benin", "Bhutan",
                "Bolivia", "Bosnia and Herzegovina", "Botswana", "Brazil",
                "Brunei", "Bulgaria", "Burkina Faso", "Burundi", "Cabo Verde",
                "Cambodia", "Cameroon", "Canada", "Central African Republic",
                "Chad", "Chile", "China", "Colombia", "Comoros", "Congo",
                "Costa Rica", "Croatia", "Cuba", "Cyprus", "Czech Republic",
                "Denmark", "Djibouti", "Dominica", "Dominican Republic",
                "Ecuador", "Egypt", "El Salvador", "Equatorial Guinea",
                "Eritrea", "Estonia", "Eswatini", "Ethiopia", "Fiji",
                "Finland", "France", "Gabon", "Gambia", "Georgia", "Germany",
                "Ghana", "Greece", "Grenada", "Guatemala", "Guinea",
                "Guinea-Bissau", "Guyana", "Haiti", "Honduras", "Hungary",
                "Iceland", "India", "Indonesia", "Iran", "Iraq", "Ireland",
                "Israel", "Italy", "Jamaica", "Japan", "Jordan", "Kazakhstan",
                "Kenya", "Kiribati", "Korea, North", "Korea, South", "Kosovo",
                "Kuwait", "Kyrgyzstan", "Laos", "Latvia", "Lebanon", "Lesotho",
                "Liberia", "Libya", "Liechtenstein", "Lithuania", "Luxembourg",
                "Madagascar", "Malawi", "Malaysia", "Maldives", "Mali", "Malta",
                "Marshall Islands", "Mauritania", "Mauritius", "Mexico",
                "Micronesia", "Moldova", "Monaco", "Mongolia", "Montenegro",
                "Morocco", "Mozambique", "Myanmar", "Namibia", "Nauru", "Nepal",
                "Netherlands", "New Zealand", "Nicaragua", "Niger", "Nigeria",
                "North Macedonia", "Norway", "Oman", "Pakistan", "Palau",
                "Palestine", "Panama", "Papua New Guinea", "Paraguay", "Peru",
                "Philippines", "Poland", "Portugal", "Qatar", "Romania",
                "Russia", "Rwanda", "Saint Kitts and Nevis", "Saint Lucia",
                "Saint Vincent and the Grenadines", "Samoa", "San Marino",
                "Sao Tome and Principe", "Saudi Arabia", "Senegal", "Serbia",
                "Seychelles", "Sierra Leone", "Singapore", "Slovakia",
                "Slovenia", "Solomon Islands", "Somalia", "South Africa",
                "South Sudan", "Spain", "Sri Lanka", "Sudan", "Suriname",
                "Sweden", "Switzerland", "Syria", "Taiwan", "Tajikistan",
                "Tanzania", "Thailand", "Timor-Leste", "Togo", "Tonga",
                "Trinidad and Tobago", "Tunisia", "Turkey", "Turkmenistan",
                "Tuvalu", "Uganda", "Ukraine", "United Arab Emirates",
                "United Kingdom", "United States", "Uruguay", "Uzbekistan",
                "Vanuatu", "Vatican City", "Venezuela", "Vietnam", "Yemen",
                "Zambia", "Zimbabwe"
            ]
            for i, country in enumerate(sample_countries, 1):
                cursor.execute("INSERT INTO countries (id, name) VALUES (?, ?)", (i, country))
            db.commit()
    
    app.run(debug=True)
