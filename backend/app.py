#!/usr/bin/env python3
"""
Egg Sorter Dashboard (RECORD-BASED)
Reads Firebase records and computes counts safely
"""

from flask import Flask, render_template, jsonify
import firebase_admin
from firebase_admin import credentials, db
from collections import defaultdict
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

    for key, r in records.items():
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

        # Recent records (last 10)
        recent.append({
            "time": r.get("timestamp"),
            "size": r.get("size"),
            "color": r.get("color"),
            "quality": r.get("quality"),
            "confidence": r.get("confidence")
        })

    # Sort recent by timestamp (newest first)
    recent.sort(key=lambda x: x["time"] or "", reverse=True)
    recent = recent[:10]

    return counters, sizes, recent


# ==============================
# Routes
# ==============================
@app.route("/")
def dashboard():
    counters, sizes, recent = compute_dashboard_data()
    return render_template(
        "dashboard.html",
        counters=counters,
        sizes=sizes,
        recent=recent
    )


@app.route("/api/data")
def api_data():
    counters, sizes, recent = compute_dashboard_data()
    return jsonify({
        "counters": counters,
        "sizes": sizes,
        "recent": recent
    })


# ==============================
# Run App
# ==============================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
