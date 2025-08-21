# app.py
# Solar Mapping & Recommendation System — Streamlit (works offline, fetches NASA POWER if online)
# Features: Map picker, monthly forecast, panel layout, economics, suitability, and a simple Q&A chatbot.
import math
import json
import time
from datetime import datetime
import requests
import numpy as np
import pandas as pd
import streamlit as st
import folium
from streamlit_folium import st_folium
import matplotlib.pyplot as plt

st.set_page_config(page_title="Solar Mapping & Recommendation System",
                   page_icon="☀️", layout="wide")

# ---------------------------- Helpers ---------------------------- #

@st.cache_data(show_spinner=False)
def fetch_nasa_power_monthly(lat, lon):
    """
    Fetch monthly average GHI (ALLSKY_SFC_SW_DWN, kWh/m2/day) from NASA POWER Climatology (2001-2020)
    Returns dict: {month_name: kWh/m2/day}
    Falls back to None on failure.
    """
    try:
        base = "https://power.larc.nasa.gov/api/temporal/climatology/point"
        params = {
            "parameters": "ALLSKY_SFC_SW_DWN",
            "community": "RE",
            "longitude": lon,
            "latitude": lat,
            "format": "JSON"
        }
        r = requests.get(base, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        values = data["properties"]["parameter"]["ALLSKY_SFC_SW_DWN"]
        # NASA returns keys like "01","02"... convert:
        month_map = {
            "01":"Jan","02":"Feb","03":"Mar","04":"Apr","05":"May","06":"Jun",
            "07":"Jul","08":"Aug","09":"Sep","10":"Oct","11":"Nov","12":"Dec"
        }
        monthly = {month_map[k]: float(v) for k,v in values.items()}
        return monthly
    except Exception:
        return None

def days_in_months(year=2024):
    # Non-leap as approx; energy is monthly average anyway.
    return {"Jan":31,"Feb":29 if (year%4==0 and (year%100!=0 or year%400==0)) else 28,
            "Mar":31,"Apr":30,"May":31,"Jun":30,"Jul":31,"Aug":31,"Sep":30,"Oct":31,"Nov":30,"Dec":31}

def deg2rad(d): return d*math.pi/180.0

def suitability_score(roof_area_m2, monthly_psh_dict, shading_factor, tilt_deg, lat):
    """Simple score 0..100 based on resource, area, shading, and tilt alignment."""
    if not monthly_psh_dict:
        resource_score = 50
    else:
        avg_psh = np.mean(list(monthly_psh_dict.values()))
        # Scale 3..7 kWh/m2/day -> 40..95
        resource_score = np.clip(20 + (avg_psh-3)*18, 20, 95)

    # Area score: 10 m2 -> 50, 30 m2 -> 80, >=60 -> 95
    area_score = 30 + np.clip((roof_area_m2-10)*1.5, 0, 65)

    # Shading_factor: 0 = none (100), 0.3 = medium (70), 0.6 = bad (40)
    shade_score = np.clip(100 - shading_factor*100, 10, 100)

    # Tilt proximity to latitude
    ideal = abs(abs(lat) - tilt_deg)
    tilt_score = np.clip(100 - ideal*2.2, 40, 100)

    weights = [0.35, 0.25, 0.2, 0.2]
    final = resource_score*weights[0] + area_score*weights[1] + shade_score*weights[2] + tilt_score*weights[3]
    return round(final, 1)

def compute_panels_fit(roof_w, roof_h, panel_w, panel_h, clearance, orientation="Portrait"):
    """
    Simple rectangular packing with constant clearance between panels and edges.
    Returns (count, rows, cols).
    orientation: 'Portrait' means panel_w x panel_h; 'Landscape' swaps dims.
    """
    if orientation == "Landscape":
        pw, ph = panel_h, panel_w
    else:
        pw, ph = panel_w, panel_h

    # effective available dims after edge clearances on all sides
    avail_w = max(roof_w - 2*clearance, 0)
    avail_h = max(roof_h - 2*clearance, 0)

    # spacing between panels = clearance (both axes)
    # For N panels in a row: N*pw + (N-1)*clearance <= avail_w
    # Solve N_w = floor((avail_w + clearance) / (pw + clearance))
    def count_axis(avail, p):
        if p <= 0: return 0
        return max(int((avail + clearance) // (p + clearance)), 0)

    cols = count_axis(avail_w, pw)
    rows = count_axis(avail_h, ph)
    count = rows * cols
    return count, rows, cols

def monthly_energy_kwh(system_kw, monthly_psh, days, performance_ratio, shading_factor):
    """
    Energy = system_kw * monthly_PSH(kWh/kW/day) * days * PR * (1 - shading_factor)
    """
    return system_kw * monthly_psh * days * performance_ratio * (1 - shading_factor)

# Simple local chatbot knowledge base
FAQ = [
    ("what is psh", "PSH = Peak Sun Hours; approx. daily solar energy in kWh per kW of PV."),
    ("what is performance ratio", "Performance Ratio (PR) lumps system losses (temperature, wiring, inverter). Typical 0.72–0.82."),
    ("how many panels", "Panels Fit depends on roof size and panel size/orientation with required clearances."),
    ("best tilt", "As a thumb rule, set tilt roughly equal to your latitude for year-round balance."),
    ("payback", "Payback Period = (Install Cost) / (Annual Savings). Lower is better.")
]

def chatbot_reply(msg):
    text = msg.lower().strip()
    if not text:
        return "Ask me anything about solar sizing, costs, tilt, or payback!"
    # keyword intents
    if "tilt" in text:
        return "Best tilt ≈ your latitude. If you want more summer energy, tilt a bit lower; for winter, tilt higher."
    if "cost" in text or "price" in text:
        return "Install cost ≈ ₹45–65k per kW (India). Adjust in the sidebar to match quotes in your area."
    if "payback" in text or "roi" in text:
        return "Payback = Install Cost / Annual Savings. Faster with higher tariffs, good sun, and net metering."
    if "panel" in text and ("how many" in text or "count" in text):
        return "Panel count depends on your roof dimensions, panel size, clearances, and chosen orientation."
    for k, v in FAQ:
        if k in text:
            return v
    return "Got it! Try asking about tilt, PR (performance ratio), costs, or how panels fit your roof."

# ---------------------------- UI ---------------------------- #

st.title("☀️ Solar Mapping & Recommendation System")

with st.sidebar:
    st.header("Inputs")
    st.markdown("**1) Location (pick on map or enter)**")

    default_lat = 21.2514  # Raipur example
    default_lon = 81.6296

    lat = st.number_input("Latitude", value=float(default_lat), format="%.6f")
    lon = st.number_input("Longitude", value=float(default_lon), format="%.6f")

    st.markdown("---")
    st.markdown("**2) Rooftop Geometry (Rectangular approximation)**")
    roof_w = st.number_input("Rooftop Width (m)", min_value=3.0, value=10.0, step=0.5)
    roof_h = st.number_input("Rooftop Height (m)", min_value=3.0, value=8.0, step=0.5)
    clearance = st.number_input("Clearance / Spacing (m)", min_value=0.0, value=0.4, step=0.1)

    st.markdown("---")
    st.markdown("**3) Panel Specs**")
    panel_w = st.number_input("Panel Width (m)", min_value=0.8, value=1.1, step=0.01, help="Shorter side of panel")
    panel_h = st.number_input("Panel Height (m)", min_value=1.2, value=1.75, step=0.01, help="Longer side of panel")
    panel_watt = st.number_input("Panel Wattage (W)", min_value=200, value=400, step=10)
    orientation = st.selectbox("Panel Orientation", ["Portrait", "Landscape"])

    st.markdown("---")
    st.markdown("**4) Performance & Costs**")
    performance_ratio = st.slider("Performance Ratio (PR)", 0.6, 0.9, 0.75, 0.01)
    shading_factor = st.slider("Shading Factor (0=None, 0.3=Medium, 0.6=High)", 0.0, 0.8, 0.1, 0.05)
    tilt_deg = st.slider("Tilt (°)", 0, 60, int(abs(lat)), 1)
    cost_per_kw = st.number_input("Installation Cost per kW (₹/kW)", min_value=10000, value=55000, step=1000)
    tariff = st.number_input("Electricity Tariff (₹/kWh)", min_value=2.0, value=8.0, step=0.5)

    st.markdown("---")
    st.caption("Tip: Click a point on the map to autofill Latitude/Longitude.")

# ---------------------------- Map Picker ---------------------------- #
st.subheader("📍 Pick Location on Map")

m = folium.Map(location=[lat, lon], zoom_start=12)
folium.Marker([lat, lon], tooltip="Selected Location").add_to(m)
returned = st_folium(m, width=700, height=400)

if returned and "last_clicked" in returned and returned["last_clicked"] is not None:
    lat = float(returned["last_clicked"]["lat"])
    lon = float(returned["last_clicked"]["lng"])
    with st.sidebar:
        st.info(f"Map selected: Lat {lat:.5f}, Lon {lon:.5f}")

# ---------------------------- Data & Calculations ---------------------------- #

st.subheader("🔆 Solar Resource (Monthly PSH)")

def fetch_solar_ghi(lat, lon):
    """
    Fetch monthly PSH (Peak Sun Hours) from NASA POWER API.
    If unavailable, fallback to PVGIS API.
    If still unavailable, use typical 5.0 kWh/m²/day average.
    """
    # --- Try NASA POWER ---
    try:
        url = f"https://power.larc.nasa.gov/api/temporal/climatology/point?parameters=ALLSKY_KT,ALLSKY_SFC_SW_DWN&community=RE&longitude={lon}&latitude={lat}&format=JSON"
        r = requests.get(url, timeout=10)
        data = r.json()
        ghi_monthly = data['properties']['parameter']['ALLSKY_SFC_SW_DWN']
        ghi_avg = np.mean(list(ghi_monthly.values()))
        return ghi_avg, ghi_monthly, "NASA POWER"
    except:
        pass

    # --- Try PVGIS ---
    try:
        url = f"https://re.jrc.ec.europa.eu/api/DRcalc?lat={lat}&lon={lon}&outputformat=json"
        r = requests.get(url, timeout=10)
        data = r.json()
        months = data['outputs']['monthly']['fixed']['E_d']  # kWh/m² per month
        ghi_monthly = {str(i+1): val/30.0 for i, val in enumerate(months)}  # convert to daily avg
        ghi_avg = np.mean(list(ghi_monthly.values()))
        return ghi_avg, ghi_monthly, "PVGIS"
    except:
        pass

    # --- Fallback Default ---
    ghi_monthly = {str(i+1): 5.0 for i in range(12)}
    return 5.0, ghi_monthly, "Fallback Avg"

# ---------------------------- Panel Fit & System Size ---------------------------- #

st.subheader("📐 Rooftop & Panel Layout")

roof_area = roof_w * roof_h
count, rows, cols = compute_panels_fit(roof_w, roof_h, panel_w, panel_h, clearance, orientation)
system_kw = round((count * panel_watt) / 1000.0, 2)

left, right = st.columns([1.2, 1])
with left:
    # Draw a simple layout grid preview
    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    ax.set_aspect('equal')
    ax.set_title(f"Layout Preview ({orientation}) — {rows} rows × {cols} cols = {count} panels")
    # Roof rectangle
    ax.add_patch(plt.Rectangle((0,0), roof_w, roof_h, fill=False, lw=2))
    # Edges clearance box
    ax.add_patch(plt.Rectangle((clearance, clearance), max(roof_w-2*clearance,0),
                               max(roof_h-2*clearance,0), fill=False, ls="--", lw=1))

    # Panel dims based on orientation
    if orientation == "Landscape":
        pw, ph = panel_h, panel_w
    else:
        pw, ph = panel_w, panel_h

    # Draw panels
    x0 = clearance
    y0 = clearance
    for r in range(rows):
        for c in range(cols):
            x = x0 + c * (pw + clearance)
            y = y0 + r * (ph + clearance)
            ax.add_patch(plt.Rectangle((x,y), pw, ph, fill=False))
    ax.set_xlim(-0.2, roof_w+0.2)
    ax.set_ylim(-0.2, roof_h+0.2)
    ax.set_xlabel("Width (m)")
    ax.set_ylabel("Height (m)")
    st.pyplot(fig)

with right:
    st.metric("Rooftop Area", f"{roof_area:.1f} m²")
    st.metric("Panels Fit", f"{count} panels")
    st.metric("System Capacity", f"{system_kw:.2f} kW")

# ---------------------------- Monthly Forecast ---------------------------- #

st.subheader("📈 Monthly Energy Output Forecast")

dim = days_in_months()
months = list(monthly_psh.keys())

monthly_energy = []
for m in months:
    e = monthly_energy_kwh(system_kw, monthly_psh[m], dim[m], performance_ratio, shading_factor)
    monthly_energy.append(e)

df = pd.DataFrame({
    "Month": months,
    "PSH (kWh/kW/day)": [round(monthly_psh[m],2) for m in months],
    "Days": [dim[m] for m in months],
    "Energy (kWh)": [round(v,1) for v in monthly_energy]
})

annual_energy = round(float(np.sum(monthly_energy)), 1)
install_cost = round(system_kw * cost_per_kw, 0)
annual_savings = round(annual_energy * tariff, 0)
payback_years = round(install_cost / max(annual_savings, 1), 1)

colA, colB, colC, colD = st.columns(4)
with colA: st.metric("Annual Solar Output", f"{annual_energy:,} kWh/yr")
with colB: st.metric("Installation Cost", f"₹{install_cost:,.0f}")
with colC: st.metric("Annual Savings", f"₹{annual_savings:,.0f}")
with colD: st.metric("Payback Period", f"{payback_years} years")

# Table + Chart
st.dataframe(df, use_container_width=True)

fig2, ax2 = plt.subplots(figsize=(7,3.5))
ax2.bar(df["Month"], df["Energy (kWh)"])
ax2.set_ylabel("Monthly Energy (kWh)")
ax2.set_title("Monthly Solar Energy Output")
st.pyplot(fig2)

# ---------------------------- Suitability ---------------------------- #

st.subheader("✅ Suitability")

score = suitability_score(roof_area, monthly_psh, shading_factor, tilt_deg, lat)
explain = []
if score >= 80: explain.append("Excellent resource & roof size.")
elif score >= 65: explain.append("Good potential — consider optimizing tilt/spacing.")
else: explain.append("Moderate potential — shading or area may be limiting.")

if shading_factor <= 0.1: explain.append("Low shading.")
elif shading_factor <= 0.3: explain.append("Some shading present.")
else: explain.append("Significant shading — trimming or relocating panels may help.")

explain.append(f"Tilt set to {tilt_deg}°, latitude ≈ {abs(lat):.0f}°.")
st.progress(min(int(score), 100))
st.write(f"**Suitability Score:** {score}/100 — " + " ".join(explain))

# ---------------------------- Chatbot ---------------------------- #

st.subheader("💬 Ask the Solar Chatbot")
if "chat" not in st.session_state:
    st.session_state.chat = [
        {"role":"assistant","content":"Hi! Ask me about panels, costs, tilt, PR, or payback."}
    ]

for m in st.session_state.chat:
    with st.chat_message(m["role"]):
        st.write(m["content"])

user_msg = st.chat_input("Type your question…")
if user_msg:
    st.session_state.chat.append({"role":"user","content":user_msg})
    reply = chatbot_reply(user_msg)
    st.session_state.chat.append({"role":"assistant","content":reply})
    with st.chat_message("user"): st.write(user_msg)
    with st.chat_message("assistant"): st.write(reply)

# ---------------------------- Summary Card ---------------------------- #

st.markdown("---")
st.subheader("📋 Summary")
st.write(f"""
- **Location:** {lat:.5f}, {lon:.5f}
- **Rooftop:** {roof_w:.1f} m × {roof_h:.1f} m (Area {roof_area:.1f} m²), Clearance {clearance:.2f} m
- **Panels:** {count} × {panel_watt} W ({orientation}), System = **{system_kw:.2f} kW**
- **Annual Output:** **{annual_energy:,} kWh**
- **Cost:** ₹{install_cost:,.0f} | **Savings:** ₹{annual_savings:,.0f}/yr | **Payback:** {payback_years} yrs
- **Suitability:** **{score}/100**
""")

st.caption("Note: Estimates are indicative. On-site shading analysis and structural checks are recommended before installation.")

