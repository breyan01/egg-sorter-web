#!/usr/bin/env python3
"""
Egg Sorter Dashboard (PURE RECORD-BASED)
- Correct PH timezone handling
- PDF reports with totals
"""

from flask import Flask, render_template, jsonify, request, send_file
import firebase_admin
from firebase_admin import credentials, db
from datetime import datetime, timezone, timedelta
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import io
import time

# ==============================
# Timezone (Philippines UTC+8)
# ==============================
PH_TZ = timezone(timedelta(hours=8))

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
# Dashboard Stats
# ==============================
def compute_dashboard_data():
    records = records_ref.get() or {}

    counters = {"total": 0, "good": 0, "bad": 0, "brown": 0, "white": 0}
    sizes = {"small": 0, "medium": 0, "large": 0, "xlarge": 0}

    for r in records.values():
        counters["total"] += 1
        counters["good" if r.get("quality") == "good" else "bad"] += 1

        if r.get("color") in counters:
            counters[r["color"]] += 1

        if r.get("size") in sizes:
            sizes[r["size"]] += 1

    return counters, sizes

# ==============================
# PDF Generator
# ==============================
def generate_pdf(title, start_time):
    records = records_ref.get() or {}

    styles = getSampleStyleSheet()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)

    elements = [Paragraph(title, styles["Title"]), Spacer(1, 12)]

    # Totals for this report
    totals = {
        "total": 0,
        "good": 0,
        "bad": 0,
        "white": 0,
        "brown": 0,
        "small": 0,
        "medium": 0,
        "large": 0,
        "xlarge": 0
    }

    table_data = [["Time (PH)", "Size", "Color", "Quality", "Confidence", "Source"]]

    for r in records.values():
        record_time = datetime.fromisoformat(r["timestamp"])
        if record_time.tzinfo is None:
            record_time = record_time.replace(tzinfo=timezone.utc)

        # Convert to PH time
        record_time_ph = record_time.astimezone(PH_TZ)

        if record_time < start_time:
            continue

        totals["total"] += 1
        totals[r["quality"]] += 1
        totals[r["color"]] += 1
        totals[r["size"]] += 1

        table_data.append([
            record_time_ph.strftime("%Y-%m-%d %H:%M:%S"),
            r["size"],
            r["color"],
            r["quality"],
            f'{round(r["confidence"] * 100, 1)}%',
            r.get("source", "auto")
        ])

    # Summary section
    summary = f"""
    <b>Total Eggs:</b> {totals["total"]}<br/>
    <b>Good:</b> {totals["good"]} | <b>Bad:</b> {totals["bad"]}<br/>
    <b>White:</b> {totals["white"]} | <b>Brown:</b> {totals["brown"]}<br/>
    <b>Small:</b> {totals["small"]},
    <b>Medium:</b> {totals["medium"]},
    <b>Large:</b> {totals["large"]},
    <b>XLarge:</b> {totals["xlarge"]}
    """

    elements.append(Paragraph(summary, styles["Normal"]))
    elements.append(Spacer(1, 16))

    table = Table(table_data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 1, colors.grey),
        ("ALIGN", (0, 0), (-1, -1), "CENTER")
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

@app.route("/api/manual_add", methods=["POST"])
def manual_add():
    data = request.json
    qty = int(data["qty"])
    now = datetime.now(timezone.utc).isoformat()

    for i in range(qty):
        record_id = f"manual_{int(time.time()*1000)}_{i}"
        records_ref.child(record_id).set({
            "size": data["size"],
            "color": data["color"],
            "quality": data["quality"],
            "confidence": 1.0,
            "source": "manual",
            "timestamp": now
        })

    return jsonify({"status": "ok"})

@app.route("/pdf/daily")
def daily_pdf():
    start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    return send_file(
        generate_pdf("Daily Egg Report", start),
        as_attachment=True,
        download_name="daily_report.pdf"
    )

@app.route("/pdf/weekly")
def weekly_pdf():
    start = datetime.now(timezone.utc) - timedelta(days=7)
    return send_file(
        generate_pdf("Weekly Egg Report", start),
        as_attachment=True,
        download_name="weekly_report.pdf"
    )

# ==============================
# Run
# ==============================
if __name__ == "__main__":
    print("Dashboard running at http://localhost:5000")
    app.run(debug=True)
