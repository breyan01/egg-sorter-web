#!/usr/bin/env python3
"""
Egg Sorter Dashboard (RECORD-BASED)
Reads Firebase records and computes counts safely
"""

from flask import Flask, render_template, jsonify, request
import firebase_admin
from firebase_admin import credentials, db
from datetime import datetime

# ==============================
# Flask App
# ==============================
app = Flask(__name__)

# ==============================
# Firebase Init
# ==============================
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred, {
    "databaseURL": "https://eggsorterproject-default-rtdb.asia-southeast1.firebasedatabase.app/"
})

records_ref = db.reference("records")


# ==============================
# Helper: Compute Stats from Records
# ==============================
def compute_dashboard_data():
    records = records_ref.get() or {}

    counters = {
        "total": 0,
        "good": 0,
        "bad": 0,
        "brown": 0,
        "white": 0
    }

    sizes = {
        "small": 0,
        "medium": 0,
        "large": 0,
        "xlarge": 0
    }

    recent = []

    for r in records.values():
        counters["total"] += 1

        # Quality
        if r.get("quality") == "good":
            counters["good"] += 1
        else:
            counters["bad"] += 1

        # Color
        color = r.get("color", "white")
        if color in counters:
            counters[color] += 1

        # Size
        size = r.get("size")
        if size in sizes:
            sizes[size] += 1

        recent.append({
            "time": r.get("timestamp"),
            "size": r.get("size"),
            "color": r.get("color"),
            "quality": r.get("quality"),
            "confidence": r.get("confidence")
        })

    recent.sort(key=lambda x: x["time"] or "", reverse=True)
    recent = recent[:10]

    return counters, sizes, recent


# ==============================
# Routes
# ==============================
@app.route("/")
def dashboard():
    return render_template("dashboard.html")


@app.route("/api/data")
def api_data():
    counters, sizes, recent = compute_dashboard_data()
    return jsonify({
        "counters": counters,
        "sizes": sizes,
        "recent": recent
    })


@app.route("/api/reset", methods=["POST"])
def api_reset():
    """Clear all egg records"""
    records_ref.delete()
    return jsonify({"status": "ok", "message": "All records cleared"})


# ==============================
# Run App
# ==============================
if __name__ == "__main__":
    print("\nDashboard running at http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)
