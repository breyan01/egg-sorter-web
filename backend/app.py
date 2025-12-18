#!/usr/bin/env python3
"""
Egg Sorting Dashboard - Clean Firebase Structure
"""

from flask import Flask, jsonify, request, render_template
from datetime import datetime, timezone
import firebase_admin
from firebase_admin import credentials, db

app = Flask(
    __name__,
    template_folder="../frontend/templates",
    static_folder="../frontend/static",
)

# Firebase
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred, {
    "databaseURL": "https://eggsorterproject-default-rtdb.asia-southeast1.firebasedatabase.app/"
})

ref_counters = db.reference("counters")
ref_sizes = db.reference("sizes")
ref_records = db.reference("records")

VALID_SIZES = {"small", "medium", "large", "xlarge"}
VALID_COLORS = {"white", "brown"}
VALID_QUALITY = {"good", "bad"}


def get_stats():
    """Get dashboard statistics"""
    counters = ref_counters.get() or {}
    sizes = ref_sizes.get() or {}
    
    # Get recent records
    records_data = ref_records.order_by_child("timestamp").limit_to_last(20).get() or {}
    
    recent = []
    for key, val in records_data.items():
        recent.append({
            "id": key,
            "size": val.get("size", ""),
            "color": val.get("color", ""),
            "quality": val.get("quality", ""),
            "confidence": val.get("confidence", 0),
            "timestamp": val.get("timestamp", ""),
        })
    
    recent.sort(key=lambda e: e["timestamp"], reverse=True)
    
    return {
        "total": int(counters.get("total", 0)),
        "good": int(counters.get("good", 0)),
        "bad": int(counters.get("bad", 0)),
        "brown": int(counters.get("brown", 0)),
        "white": int(counters.get("white", 0)),
        "sizes": {
            "small": int(sizes.get("small", 0)),
            "medium": int(sizes.get("medium", 0)),
            "large": int(sizes.get("large", 0)),
            "xlarge": int(sizes.get("xlarge", 0)),
        },
        "recent": recent
    }


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/stats")
def api_stats():
    return jsonify(get_stats())


@app.route("/api/egg", methods=["POST"])
def api_add_egg():
    """Manually add egg (for testing)"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400
    
    size = data.get("size", "").lower()
    color = data.get("color", "").lower()
    quality = data.get("quality", "").lower()
    
    if size not in VALID_SIZES:
        return jsonify({"error": f"Invalid size. Use: {VALID_SIZES}"}), 400
    if color not in VALID_COLORS:
        return jsonify({"error": f"Invalid color. Use: {VALID_COLORS}"}), 400
    if quality not in VALID_QUALITY:
        return jsonify({"error": f"Invalid quality. Use: {VALID_QUALITY}"}), 400
    
    # Increment counters
    def inc(path):
        ref = db.reference(path)
        def txn(val):
            return (val or 0) + 1
        ref.transaction(txn)
    
    inc("counters/total")
    inc(f"counters/{quality}")
    inc(f"counters/{color}")
    inc(f"sizes/{size}")
    
    # Add record
    record = {
        "size": size,
        "color": color,
        "quality": quality,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "web-dashboard",
        "confidence": 1.0
    }
    
    new_ref = ref_records.push(record)
    record["id"] = new_ref.key
    
    return jsonify({"message": "Egg recorded", "egg": record}), 201


@app.route("/api/reset", methods=["POST"])
def api_reset():
    """Reset all data"""
    # Reset counters
    ref_counters.set({
        "total": 0,
        "good": 0,
        "bad": 0,
        "brown": 0,
        "white": 0
    })
    
    # Reset sizes
    ref_sizes.set({
        "small": 0,
        "medium": 0,
        "large": 0,
        "xlarge": 0
    })
    
    # Delete records
    ref_records.delete()
    
    return jsonify({"message": "All data reset"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)