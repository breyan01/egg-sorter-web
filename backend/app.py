#!/usr/bin/env python3
"""
Egg Sorter Dashboard (RECORD-BASED)
Dashboard-only reset, Manual Add (max 5),
Daily & Weekly PDF Reports with SOURCE field (PH Timezone)
"""

from flask import Flask, render_template, jsonify, request, send_file
import firebase_admin
from firebase_admin import credentials, db
from datetime import datetime, timedelta, timezone
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
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
# PDF Generator (WITH SOURCE)
# ==============================
def generate_pdf(title, start_time):
    records = records_ref.get() or {}

    # Filter records by time
    filtered = []
    for r in records.values():
        rt = datetime.fromisoformat(r["timestamp"])
        if rt >= start_time:
            filtered.append(r)

    # Sort by timestamp (newest first)
    filtered.sort(key=lambda x: x["timestamp"], reverse=True)

    total_count = len(filtered)

    # Count by source
    sorter_count = sum(1 for r in filtered if r.get("source") in ["ai-sorter", "sequential-sorter"])
    manual_count = sum(1 for r in filtered if r.get("source") == "manual")

    # Summary by size/color/quality
    summary = {}
    for r in filtered:
        key = (r["size"], r["color"], r["quality"])
        summary[key] = summary.get(key, 0) + 1

    # Build PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    # Title
    elements.append(Paragraph(f"<b>{title}</b>", styles["Title"]))
    elements.append(Spacer(1, 12))

    # Report info
    elements.append(Paragraph(f"<b>Generated:</b> {datetime.now(PH_TZ).strftime('%Y-%m-%d %H:%M:%S')}", styles["Normal"]))
    elements.append(Paragraph(f"<b>Total Eggs:</b> {total_count}", styles["Heading2"]))
    elements.append(Paragraph(f"<b>From Sorter:</b> {sorter_count}", styles["Normal"]))
    elements.append(Paragraph(f"<b>Manual Add:</b> {manual_count}", styles["Normal"]))
    elements.append(Spacer(1, 20))

    # Summary Table
    elements.append(Paragraph("<b>Summary by Category</b>", styles["Heading2"]))
    elements.append(Spacer(1, 12))

    summary_table_data = [["Size", "Color", "Quality", "Count"]]
    for (size, color, quality), count in sorted(summary.items()):
        summary_table_data.append([size, color, quality, str(count)])

    summary_table = Table(summary_table_data)
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.grey),
        ("TEXTCOLOR", (0,0), (-1,0), colors.whitesmoke),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,0), 12),
        ("BOTTOMPADDING", (0,0), (-1,0), 12),
        ("BACKGROUND", (0,1), (-1,-1), colors.beige),
        ("GRID", (0,0), (-1,-1), 1, colors.black)
    ]))

    elements.append(summary_table)
    elements.append(Spacer(1, 30))

    # Detailed Records Table (WITH SOURCE)
    elements.append(Paragraph("<b>Detailed Records</b>", styles["Heading2"]))
    elements.append(Spacer(1, 12))

    records_table_data = [["#", "Size", "Color", "Quality", "Source", "Timestamp"]]
    
    for idx, r in enumerate(filtered[:100], 1):  # Show max 100 records
        timestamp = datetime.fromisoformat(r["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
        source = r.get("source", "unknown")
        
        # Simplify source names for display
        if source in ["ai-sorter", "sequential-sorter"]:
            source_display = "Sorter"
        elif source == "manual":
            source_display = "Manual"
        else:
            source_display = source
        
        records_table_data.append([
            str(idx),
            r["size"],
            r["color"],
            r["quality"],
            source_display,
            timestamp
        ])

    records_table = Table(records_table_data)
    records_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.grey),
        ("TEXTCOLOR", (0,0), (-1,0), colors.whitesmoke),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,0), 10),
        ("BOTTOMPADDING", (0,0), (-1,0), 12),
        ("BACKGROUND", (0,1), (-1,-1), colors.beige),
        ("GRID", (0,0), (-1,-1), 1, colors.black),
        ("FONTSIZE", (0,1), (-1,-1), 8)
    ]))

    elements.append(records_table)

    if len(filtered) > 100:
        elements.append(Spacer(1, 12))
        elements.append(Paragraph(f"<i>Showing first 100 of {total_count} records</i>", styles["Normal"]))

    # Build PDF
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
            "source": "manual",  # Mark as manual entry
            "timestamp": datetime.now(PH_TZ).isoformat()
        })

    return jsonify({"status": "ok"})

@app.route("/api/reset", methods=["POST"])
def reset_dashboard():
    # Dashboard-only reset (does nothing to records)
    return jsonify({"status": "ok"})

@app.route("/report/daily")
def daily_report():
    start = datetime.now(PH_TZ).replace(hour=0, minute=0, second=0, microsecond=0)
    pdf = generate_pdf("Daily Egg Report", start)
    return send_file(pdf, as_attachment=True, download_name="daily_report.pdf", mimetype="application/pdf")

@app.route("/report/weekly")
def weekly_report():
    start = datetime.now(PH_TZ) - timedelta(days=7)
    pdf = generate_pdf("Weekly Egg Report", start)
    return send_file(pdf, as_attachment=True, download_name="weekly_report.pdf", mimetype="application/pdf")

# ==============================
# Run App
# ==============================
if __name__ == "__main__":
    print("\n" + "="*60)
    print("EGG SORTER DASHBOARD")
    print("="*60)
    print("Dashboard running at http://localhost:5000")
    print("Features:")
    print("  - Real-time stats")
    print("  - Manual add (max 5 eggs)")
    print("  - Daily & Weekly PDF reports (with source)")
    print("="*60 + "\n")
    app.run(debug=True)