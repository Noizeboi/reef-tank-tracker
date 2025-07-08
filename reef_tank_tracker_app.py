# reef_tank_tracker_app.py - Final Stable Version (repaired & cleaned)

import streamlit as st
import json
import pandas as pd
import os
from datetime import datetime
from fpdf import FPDF
from io import BytesIO

# Constants
SAVE_FILE = "reef_data.json"
IMAGE_DIR = "images"
os.makedirs(IMAGE_DIR, exist_ok=True)

# Initialize Session State
defaults = {
    "selected_tank": None,
    "tanks": {},
    "custom_modes": {}
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# Helper Functions
def strip_unicode(text):
    return text.encode("latin-1", errors="ignore").decode("latin-1")

def load_tanks():
    try:
        with open(SAVE_FILE, "r") as f:
            data = json.load(f)
        st.session_state.tanks = data.get("tanks", {})
        st.session_state.custom_modes = data.get("custom_modes", {})
    except FileNotFoundError:
        st.session_state.tanks = {}
        st.session_state.custom_modes = {}

def save_tanks():
    with open(SAVE_FILE, "w") as f:
        json.dump({
            "tanks": st.session_state.tanks,
            "custom_modes": st.session_state.custom_modes
        }, f)

# PDF Export
def generate_pdf_report(tank_name, tank_data, suggestions):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    pdf.cell(200, 10, txt=strip_unicode(f"Tank Report: {tank_name}"), ln=True)
    pdf.cell(200, 10, txt="Latest Parameters:", ln=True)

    latest = tank_data.get("data", [])[-1] if tank_data.get("data") else {}
    for key, value in latest.items():
        pdf.cell(200, 8, txt=strip_unicode(f"{key}: {value}"), ln=True)

    if suggestions:
        pdf.cell(200, 10, txt="Suggested Maintenance:", ln=True)
        for tip in suggestions:
            pdf.multi_cell(0, 8, strip_unicode(f"• {tip}"))

    pdf_buffer = BytesIO()
    pdf.output(pdf_buffer)
    pdf_buffer.seek(0)
    return pdf_buffer
