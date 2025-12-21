#!/usr/bin/env python3
"""
Egg Sorter Dashboard (RECORD-BASED)
Dashboard-only reset, Manual Add (max 5),
Daily & Weekly PDF Reports (PH Timezone)
"""

from flask import Flask, render_template, jsonify, request, send_file
import firebase_admin
from firebase_admin import credentials, db
from datetime import datetime, timedelta, timezone
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import io

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

PH_TZ = timezone(timedelta(hours=8))

# ==============================
# Helper: Compute Stats
# ==============================
def compute_dashboard_data():
    records = records_ref.get() or {}

    counters = dict(total=0, good=0, bad=0, brown=0, white=0)
    sizes = dict(small=0, medium=0, large=0, xlarge=0)

    for r in records.values():
        counters["total"] += 1
        counters[r["quality"]] += 1
        counters[r["color"]] += 1
        sizes[r["size"]] += 1

    return counters, sizes

# ==============================
# PDF Generator
# ==============================
def generate_pdf(title, start_time):
    records = records_ref.get() or {}

    filtered = []
    for r in records.values():
        rt = datetime.fromisoformat(r["timestamp"])
        if rt >= start_time:
            filtered.append(r)

    total_count = len(filtered)

    summary = {}
    for r in filtered:
        key = (r["size"], r["color"], r["quality"])
        summary[key] = summary.get(key, 0) + 1

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()

    elements = [
        Paragraph(f"<b>{title}</b>", styles["Title"]),
        Paragraph(f"Generated: {datetime.now(PH_TZ).strftime('%Y-%m-%d %H:%M:%S')}", styles["Normal"]),
        Paragraph(f"<b>Total Eggs: {total_count}</b>", styles["Heading2"]),
    ]

    table_data = [["Size", "Color", "Quality", "Count"]]
    for (size, color, quality), count in summary.items():
        table_data.append([size, color, quality, count])

    table = Table(table_data)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.grey),
        ("GRID", (0,0), (-1,-1), 1, colors.black),
        ("ALIGN", (0,0), (-1,-1), "CENTER")
    ]))

    elements.append(table)
    doc.build(elements)
    buffer.seek(0)
    return buffer

# ==============================
# Routes
# ==============================
@app.route("/")
def dashboard():
    return render_template("dashboard.html")

@app.route("/api/data")
def api_data():
    counters, sizes = compute_dashboard_data()
    return jsonify({"counters": counters, "sizes": sizes})

@app.route("/api/manual-add", methods=["POST"])
def manual_add():
    data = request.json
    qty = int(data["qty"])

    if qty < 1 or qty > 5:
        return jsonify({"error": "Max manual add is 5 eggs"}), 400

    for _ in range(qty):
        records_ref.push({
            "size": data["size"],
            "color": data["color"],
            "quality": data["quality"],
            "confidence": 1.0,
            "timestamp": datetime.now(PH_TZ).isoformat()
        })

    return jsonify({"status": "ok"})

@app.route("/api/reset", methods=["POST"])
def reset_dashboard():
    return jsonify({"status": "ok"})

@app.route("/report/daily")
def daily_report():
    start = datetime.now(PH_TZ).replace(hour=0, minute=0, second=0)
    pdf = generate_pdf("Daily Egg Report", start)
    return send_file(pdf, as_attachment=True, download_name="daily_report.pdf")

@app.route("/report/weekly")
def weekly_report():
    start = datetime.now(PH_TZ) - timedelta(days=7)
    pdf = generate_pdf("Weekly Egg Report", start)
    return send_file(pdf, as_attachment=True, download_name="weekly_report.pdf")

# ==============================
# Run App
# ==============================
if __name__ == "__main__":
    print("Dashboard running at http://localhost:5000")
    app.run(debug=True)
