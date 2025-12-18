#!/usr/bin/env python3
"""
Egg Sorting Machine Web Dashboard
Backend: Flask API + Firebase Realtime Database

Uses your existing Firebase structure:

root
 ├─ bad: <int>
 ├─ good: <int, optional>
 ├─ brown: <int, optional>
 ├─ eggCount: <int>
 └─ eggs
     └─ history
         ├─ small: <int>
         ├─ medium: <int>
         ├─ large: <int>
         ├─ xlarge: <int>
         └─ resetInProgress: bool

We also add a new node:
  eggs/records   ← to show "recent eggs" in dashboard
"""

from flask import Flask, jsonify, request, render_template
from datetime import datetime, timezone
import firebase_admin
from firebase_admin import credentials, db

# ------------------------------
# Flask setup
# ------------------------------
app = Flask(
    __name__,
    template_folder="../frontend/templates",
    static_folder="../frontend/static",
)

# ------------------------------
# Firebase setup
# ------------------------------
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred, {
    "databaseURL": "https://eggsorterproject-default-rtdb.asia-southeast1.firebasedatabase.app/"
})

# Firebase reference shortcuts
ref_root = db.reference("/")
ref_history = db.reference("eggs/history")
ref_records = db.reference("eggs/records")

VALID_SIZES = {"small", "medium", "large", "xlarge"}
VALID_COLORS = {"white", "brown", "other"}
VALID_QUALITY = {"good", "bad"}


# ------------------------------
# Helpers
# ------------------------------
def _inc(path: str, amount: int = 1):
    """Increment a Firebase numeric field safely."""
    ref = db.reference(path)

    def txn(value):
        if value is None:
            value = 0
        return int(value) + amount

    ref.transaction(txn)


def get_stats():
    """Pull dashboard statistics from Firebase."""
    root = ref_root.get() or {}
    history = (root.get("eggs") or {}).get("history", {})

    total = int(root.get("eggCount", 0) or 0)

    size_counts = {
        "small": int(history.get("small", 0)),
        "medium": int(history.get("medium", 0)),
        "large": int(history.get("large", 0)),
        "xlarge": int(history.get("xlarge", 0)),
    }

    quality_counts = {
        "good": int(root.get("good", 0)),
        "bad": int(root.get("bad", 0)),
    }

    # Recent eggs
    records = ref_records.order_by_child("timestamp").limit_to_last(20).get() or {}

    recent = []
    for key, val in records.items():
        recent.append({
            "id": key,
            "size": val.get("size", ""),
            "color": val.get("color", ""),
            "quality": val.get("quality", ""),
            "timestamp": val.get("timestamp", ""),
        })

    recent.sort(key=lambda e: e["timestamp"], reverse=True)

    return {
        "total": total,
        "sizes": size_counts,
        "quality": quality_counts,
        "recent": recent,
    }


# ------------------------------
# Routes
# ------------------------------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/stats")
def api_stats():
    return jsonify(get_stats())


@app.route("/api/egg", methods=["POST"])
def api_add_egg():
    """Add a new egg record."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    size = data.get("size", "").lower()
    color = data.get("color", "").lower()
    quality = data.get("quality", "").lower()

    if size not in VALID_SIZES:
        return jsonify({"error": "Invalid size"}), 400
    if color not in VALID_COLORS:
        return jsonify({"error": "Invalid color"}), 400
    if quality not in VALID_QUALITY:
        return jsonify({"error": "Invalid quality"}), 400

    timestamp = datetime.now(timezone.utc).isoformat()

    egg_data = {
        "size": size,
        "color": color,
        "quality": quality,
        "timestamp": timestamp,
        "source": "web-dashboard",
    }

    # Update counters
    _inc("eggCount", 1)
    _inc(f"eggs/history/{size}", 1)
    _inc(quality, 1)
    if color == "brown":
        _inc("brown", 1)

    # Add to recent records
    new_ref = ref_records.push(egg_data)
    egg_data["id"] = new_ref.key

    return jsonify({"message": "Egg recorded", "egg": egg_data}), 201


@app.route("/api/reset", methods=["POST"])
def api_reset():
    """Reset counters + records."""
    for key in ["eggCount", "good", "bad", "brown"]:
        ref_root.child(key).set(0)

    for size in VALID_SIZES:
        ref_history.child(size).set(0)

    ref_records.delete()

    return jsonify({"message": "All Firebase data reset"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
