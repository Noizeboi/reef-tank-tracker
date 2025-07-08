def suggest_maintenance(tank):
    suggestions = []

    mode = tank.get("mode", "Fish Only")
    equipment = tank.get("equipment", [])
    data = tank.get("data", [])
    maintenance = tank.get("maintenance", [])

    latest = data[-1] if data else {}
    get_val = lambda x: float(latest.get(x, 0)) if latest.get(x) not in [None, '', 'N/A'] else None

    nitrate = get_val("Nitrate (ppm)")
    phosphate = get_val("Phosphate (ppm)")
    ammonia = get_val("Ammonia (ppm)")
    pH = get_val("pH")
    alk = get_val("Alkalinity (dKH)")

    if nitrate and nitrate > 40:
        suggestions.append("Nitrate is high – perform 20–30% water change and clean filter media.")
    if phosphate and phosphate > 0.1:
        suggestions.append("Phosphate elevated – replace GFO or reduce feeding.")
    if ammonia and ammonia > 0.25:
        suggestions.append("Toxic ammonia detected – urgent water change recommended.")
    if pH and pH < 7.9:
        suggestions.append("Low pH – improve aeration or review CO₂ levels.")
    if alk and ((mode == "SPS" and (alk < 7.5 or alk > 8.5)) or (mode == "LPS" and (alk < 7 or alk > 12))):
        suggestions.append("Alkalinity instability – dose buffer or use auto-doser.")

    if "Skimmer" in equipment:
        from datetime import datetime
        now = datetime.now()
        clean_logs = [e for e in maintenance if "skimmer" in e.get("Task", "").lower()]
        if clean_logs:
            last_clean = max([datetime.strptime(e["Date"], "%Y-%m-%d") for e in clean_logs])
            days = (now - last_clean).days
            if days > 10:
                suggestions.append(f"Skimmer last cleaned {days} days ago – clean recommended.")
        else:
            suggestions.append("Skimmer installed but never cleaned – log a clean soon.")

    if "Heater" in equipment:
        suggestions.append("Check heater calibration monthly to avoid temperature drift.")

    if mode == "SPS":
        suggestions.append("SPS coral requires stable parameters – test calcium, alk, mag regularly.")

    return suggestions



import streamlit as st

# Utility to strip non-Latin1 characters for PDF safety
def strip_unicode(text):
    return text.encode("latin-1", errors="ignore").decode("latin-1")

# Load dropdown models early
import json
try:
    with open("dropdown_models.json", "r") as f:
        dropdown_models = json.load(f)
except FileNotFoundError:
    dropdown_models = {}
    import streamlit as st
    st.error("Missing dropdown_models.json – please check your repository.")
import pandas as pd
import json
import os
from datetime import datetime
from fpdf import FPDF
import matplotlib.pyplot as plt

# Initialize session state
defaults = {
    "selected_tank": None,
    "tanks": {},
    "custom_modes": {}
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

SAVE_FILE = "reef_data.json"
IMAGE_DIR = "images"
os.makedirs(IMAGE_DIR, exist_ok=True)

# Load and Save
def load_tanks():
    if os.path.exists(SAVE_FILE):
        with open(SAVE_FILE, "r") as f:
            data = json.load(f)
            st.session_state.custom_modes = data.get("custom_modes", {})
            tanks = data.get("tanks", {})
            for t in tanks.values():
                img = t.get("profile_image")
                if isinstance(img, str) and not os.path.exists(os.path.join(IMAGE_DIR, img)):
                    t["profile_image"] = None
            return tanks
    return {}

def save_tanks():
    with open(SAVE_FILE, "w") as f:
        json.dump({
            "tanks": st.session_state.tanks,
            "custom_modes": st.session_state.custom_modes
        }, f, indent=2, default=str)

# Default modes
default_modes = {
    "Fish Only": {
        "Temperature (°C)": (24, 27),
        "Salinity (SG)": (1.020, 1.026),
        "pH": (7.8, 8.4),
        "Ammonia (ppm)": (0, 0.25),
        "Nitrite (ppm)": (0, 0.5),
        "Nitrate (ppm)": (0, 40)
    },
    "LPS": {
        "Temperature (°C)": (24, 26),
        "Salinity (SG)": (1.024, 1.026),
        "pH": (8.0, 8.4),
        "Ammonia (ppm)": (0, 0),
        "Nitrite (ppm)": (0, 0),
        "Nitrate (ppm)": (0, 20),
        "Phosphate (ppm)": (0, 0.1),
        "Calcium (ppm)": (380, 450),
        "Alkalinity (dKH)": (7, 12),
        "Magnesium (ppm)": (1200, 1400)
    },
    "SPS": {
        "Temperature (°C)": (25, 26),
        "Salinity (SG)": (1.025, 1.026),
        "pH": (8.1, 8.4),
        "Ammonia (ppm)": (0, 0),
        "Nitrite (ppm)": (0, 0),
        "Nitrate (ppm)": (0, 5),
        "Phosphate (ppm)": (0, 0.03),
        "Calcium (ppm)": (400, 450),
        "Alkalinity (dKH)": (7.5, 8.5),
        "Magnesium (ppm)": (1300, 1400)
    }
}
combined_modes = {**default_modes, **st.session_state.custom_modes}

def check_alerts(params, mode):
    alerts = []
    for param, (low, high) in combined_modes.get(mode, {}).items():
        try:
            val = float(params.get(param, 'N/A'))
            if val < low or val > high:
                alerts.append(f"{param}: {val} (Expected: {low}-{high})")
        except:
            continue
    return alerts

def highlight_outliers(row, mode):
    styles = []
    for col in row.index:
        if col in combined_modes[mode]:
            val = row[col]
            low, high = combined_modes[mode][col]
            if pd.notnull(val) and (val < low or val > high):
                styles.append("background-color: #ffcccc")
            else:
                styles.append("")
        else:
            styles.append("")
    return styles

# Load tanks
st.session_state.tanks = load_tanks()
if st.session_state.selected_tank not in st.session_state.tanks:
    st.session_state.selected_tank = next(iter(st.session_state.tanks), None)

# Sidebar
with st.sidebar:
    st.header("🌊 Reef Tank Tracker")
    tank_name = st.text_input("Add New Tank")
    if st.button("➕ Add Tank") and tank_name:
        st.session_state.tanks[tank_name] = {
            "display_capacity": None,
            "sump_capacity": None,
            "theme": "",
            "livestock": "",
            "equipment": [],
            "profile_image": None,
            "mode": "Fish Only",
            "data": [],
            "maintenance": [],
            "diary": []
        }
        st.session_state.selected_tank = tank_name
        save_tanks()

    if st.session_state.tanks:
        st.session_state.selected_tank = st.selectbox("Select Tank", list(st.session_state.tanks.keys()), index=0)

    st.button("💾 Save All", on_click=save_tanks)

    # Add + edit custom modes
    with st.expander("➕ Create Custom Mode"):
        new_mode = st.text_input("New Mode Name")
        param = st.text_input("Parameter Name")
        low = st.number_input("Min", value=0.0)
        high = st.number_input("Max", value=1.0)
        if st.button("Add to Custom Mode") and new_mode and param:
            st.session_state.custom_modes.setdefault(new_mode, {})[param] = (low, high)
            st.success(f"Added {param} to {new_mode}")
        if st.button("Save This Mode") and new_mode in st.session_state.custom_modes:
            save_tanks()
            st.success(f"Saved mode: {new_mode}")

    with st.expander("🛠️ Manage Custom Modes"):
        if st.session_state.custom_modes:
            sel = st.selectbox("Edit Mode", list(st.session_state.custom_modes.keys()))
            updated = {}
            for param, (low, high) in st.session_state.custom_modes[sel].items():
                col1, col2, col3, col4 = st.columns([4, 2, 2, 1])
                with col1:
                    st.markdown(f"**{param}**")
                with col2:
                    new_low = st.number_input(f"Min {param}", value=low, key=f"{param}_min")
                with col3:
                    new_high = st.number_input(f"Max {param}", value=high, key=f"{param}_max")
                with col4:
                    remove = st.checkbox("❌", key=f"{param}_rm")
                if not remove:
                    updated[param] = (new_low, new_high)
            if st.button("💾 Save Changes"):
                st.session_state.custom_modes[sel] = updated
                save_tanks()
                st.success(f"Updated mode: {sel}")
            if st.button("🗑️ Delete This Mode"):
                del st.session_state.custom_modes[sel]
                save_tanks()
                st.experimental_rerun()

# Main Interface
st.title("🧪 Marine Reef Tank Tracker")

if st.session_state.selected_tank:
    tank = st.session_state.tanks[st.session_state.selected_tank]
    tabs = st.tabs(["Overview", "Log Parameters", "Maintenance", "Diary", "Trends"])

    with tabs[0]:
        st.subheader("Tank Overview")
        if tank.get("profile_image"):
            img_path = os.path.join(IMAGE_DIR, tank["profile_image"])
            if os.path.exists(img_path):
                st.image(img_path, use_container_width=True)
        with st.form("tank_config"):
            tank["mode"] = st.selectbox("Mode", list(combined_modes.keys()), index=list(combined_modes).index(tank.get("mode", "Fish Only")))
            tank["theme"] = st.text_input("Theme", tank.get("theme", ""))
            tank["livestock"] = st.text_area("Livestock", tank.get("livestock", ""))
            tank["display_capacity"] = st.number_input("Display Capacity (L)", value=tank.get("display_capacity") or 0.0)
            tank["sump_capacity"] = st.number_input("Sump Capacity (L)", value=tank.get("sump_capacity") or 0.0)
            available_equipment = ["Heater", "LED Light", "Skimmer", "Auto Top-Off"]
        # 🔧 Equipment Selection
            submitted = st.form_submit_button("Submit")

# Equipment Configuration - Safe, Form-Free Version
import json
try:
    with open("dropdown_models.json", "r") as f:
        dropdown_models = json.load(f)
except Exception:
    dropdown_models = {}
    st.error("Failed to load 'dropdown_models.json'. Please check the file.")

equipment_options = {
    "Heater": dropdown_models.get("Heaters", []),
    "LED Light": dropdown_models.get("LED Lights", []),
    "Skimmer": dropdown_models.get("Skimmers", []),
    "ATO System": dropdown_models.get("ATO Systems", []),
    "Return Pump": dropdown_models.get("Return Pumps", []),
    "Overflow Type": dropdown_models.get("Overflows", []),
}

with st.expander("🔧 Equipment Configuration", expanded=True):
    tank["selected_equipment"] = tank.get("selected_equipment", {})
    updated = False
    for eq_type, options in equipment_options.items():
        current = tank["selected_equipment"].get(eq_type)
        index = options.index(current) if current in options else 0 if options else 0
        selected = st.selectbox(
            f"{eq_type} Model",
            options,
            index=index,
            key=f"{eq_type}_select"
        )
        if selected != current:
            tank["selected_equipment"][eq_type] = selected
            updated = True

    if st.button("Save Equipment Settings"):
        if updated:
            st.success("Equipment updated.")
        else:
            st.info("No changes detected.")

        validation_notes = []
        display_vol = tank.get("display_capacity", 0.0)
        sump_vol = tank.get("sump_capacity", 0.0)
        total_volume = display_vol + sump_vol

        from json import load as json_load
        with open("equipment_model_lookup.json", "r") as ef:
            model_lookup = json_load(ef)

        # Heater wattage check
        heater = tank["selected_equipment"].get("Heater")
        if heater in model_lookup:
            wattage = model_lookup[heater].get("wattage")
            if wattage and (total_volume / wattage > 3):  # Rough guide: 1W per 3L
                validation_notes.append(f"Heater '{heater}' may be underpowered for {total_volume}L.")

        # Skimmer tank rating check
        skimmer = tank["selected_equipment"].get("Skimmer")
        if skimmer in model_lookup:
            rated = model_lookup[skimmer].get("rated_tank_l")
            if rated and rated < total_volume:
                validation_notes.append(f"Skimmer '{skimmer}' is rated for {rated}L, which is under your tank volume.")

        # Return pump vs overflow flow
        pump = tank["selected_equipment"].get("Return Pump")
        overflow = tank["selected_equipment"].get("Overflow Type")
        if pump in model_lookup and overflow in model_lookup:
            pump_flow = model_lookup[pump].get("flow_lph")
            overflow_limit = model_lookup[overflow].get("recommended_flow_lph")
            if pump_flow and overflow_limit and pump_flow > overflow_limit:
                validation_notes.append(f"Pump '{pump}' may exceed overflow capacity '{overflow}' ({overflow_limit} L/h).")

        if validation_notes:
            st.warning("⚠️ Equipment Mismatch Detected:")
            for note in validation_notes:
                st.write(f"• {note}")
            profile_pic = st.file_uploader("Profile Image", type=["jpg", "png", "jpeg"])
            if st.form_submit_button("Save Tank"):
                if profile_pic:
                    filename = f"{st.session_state.selected_tank}_profile_{profile_pic.name}"
                    with open(os.path.join(IMAGE_DIR, filename), "wb") as f:
                        f.write(profile_pic.read())
                    tank["profile_image"] = filename
                save_tanks()
                st.success("Saved")

    with tabs[1]:
        st.subheader("Log Parameters")
        with st.form("log_params"):
            log = {"Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
            for param in combined_modes[tank["mode"]].keys():
                log[param] = st.text_input(param)
            if st.form_submit_button("Submit Log"):
                tank["data"].append(log)
                save_tanks()
                st.success("Logged")

    with tabs[2]:
        st.subheader("Maintenance")
        with st.form("maintenance_form"):
            m_date = st.date_input("Date", datetime.now())
            task = st.text_input("Task")
            notes = st.text_area("Notes")
            if st.form_submit_button("Add Entry"):
                tank["maintenance"].append({"Date": str(m_date), "Task": task, "Notes": notes})
                save_tanks()
                st.success("Added")

    with tabs[3]:
        st.subheader("Diary")
        with st.form("diary_form"):
            d_date = st.date_input("Entry Date", datetime.now())
            d_note = st.text_area("Note")
            d_image = st.file_uploader("Image", type=["png", "jpg", "jpeg"])
            if st.form_submit_button("Add Entry"):
                entry = {"Date": str(d_date), "Entry": d_note}
                if d_image:
                    img_path = os.path.join(IMAGE_DIR, d_image.name)
                    with open(img_path, "wb") as f:
                        f.write(d_image.read())
                    entry["Image"] = d_image.name
                tank["diary"].append(entry)
                save_tanks()
                st.success("Added")

    with tabs[4]:
        if tank["data"]:
            df = pd.DataFrame(tank["data"])
            st.subheader("Latest Logs")
            df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
            numeric_df = df.drop(columns=["Date"], errors="ignore").apply(pd.to_numeric, errors="coerce")
            styled = numeric_df.copy()
            styled["Date"] = df["Date"]
            styled_df = styled.style.apply(highlight_outliers, axis=1, mode=tank["mode"])
            st.dataframe(styled_df)
            try:
                last = df.iloc[-1].to_dict()
                alerts = check_alerts(last, tank["mode"])
                if alerts:
                    st.toast("⚠️ Parameter Alert: Out-of-range values found.")
                    for alert in alerts:
                        st.warning(alert)
            except:
                pass
            st.line_chart(numeric_df.set_index(df["Date"]))


# Inject suggested maintenance into Overview and Maintenance Tabs
    with tabs[0]:
        st.subheader("Tank Overview")
        if tank.get("profile_image"):
            img_path = os.path.join(IMAGE_DIR, tank["profile_image"])
            if os.path.exists(img_path):
                st.image(img_path, use_container_width=True)

        # --- Suggested Overview Actions ---
        overview_suggestions = suggest_maintenance(tank)[:2]
        if overview_suggestions:
            st.markdown("### ⚠️ Suggested Actions")
            for s in overview_suggestions:
                st.info(s)

    with tabs[2]:
        st.subheader("Maintenance")
        with st.expander("💡 Suggested Maintenance", expanded=False):
            full_suggestions = suggest_maintenance(tank)
            if full_suggestions:
                for tip in full_suggestions:
                    st.write("• " + tip)
            else:
                st.write("✅ No immediate suggestions – tank appears healthy.")


        with tabs[4]:
            st.subheader("Export & Trends")
            export_suggestions = suggest_maintenance(tank)
            include_suggestions = st.checkbox("Include Suggestions in PDF Export")

            # Export PDF
            if st.button("📄 Download PDF Report"):
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", size=12)
                pdf.cell(200, 10, txt=strip_unicode(f"Tank Report: {st.session_state.selected_tank}"), ln=True)
                pdf.cell(200, 10, txt=strip_unicode(f"Theme: {tank.get('theme', '')}"), ln=True)
                pdf.cell(200, 10, txt=strip_unicode(f"Livestock: {tank.get('livestock', '')}"), ln=True)
                pdf.cell(200, 10, txt=strip_unicode(f"Mode: {tank.get('mode', '')}"), ln=True)

                if tank["data"]:
                    last_log = tank["data"][-1]
                    pdf.cell(200, 10, txt=strip_unicode("Latest Parameters:"), ln=True)
                    for k, v in last_log.items():
                        pdf.cell(200, 8, txt=strip_unicode(f"{k}: {v}"), ln=True)

                if include_suggestions and export_suggestions:
                    pdf.cell(200, 10, txt=strip_unicode("Suggested Maintenance:"), ln=True)
                    for tip in export_suggestions:
                        pdf.cell(200, 8, txt=strip_unicode(f"• {tip}"), ln=True)

                pdf_output_path = "/mnt/data/tank_report.pdf"
                pdf.output(pdf_output_path)
                with open(pdf_output_path, "rb") as f:
                    st.download_button("📄 Save PDF", f, file_name="tank_report.pdf")
