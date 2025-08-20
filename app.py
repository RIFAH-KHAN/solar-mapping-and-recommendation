# app.py
import streamlit as st
import numpy as np
import math
import requests
from io import BytesIO
from PIL import Image
import matplotlib.pyplot as plt
from fpdf import FPDF
import folium
from streamlit_folium import st_folium
from folium.plugins import Draw

st.set_page_config(page_title="Solar Mapping & Recommendation", layout="wide")

# ------------------------
# Header with slogan & image
# ------------------------
st.image("https://images.unsplash.com/photo-1509395176047-4a66953fd231?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=MnwxMjA3fDB8MHxzZWFyY2h8Mnx8c29sYXIlMjBwYW5lbHxlbnwwfHwwfHw%3D&ixlib=rb-4.0.3&q=80&w=800", use_column_width=True)
st.title("🌞 Solar Mapping & Recommendation System")
st.markdown("**Clean energy for a brighter future!** Harness your rooftop's solar potential today.")

# ------------------------
# Map + Polygon Drawing
# ------------------------
st.subheader("Draw Your Rooftop Boundary")

# default map center
map_center = [20.3, 85.8]  # Raipur approx
m = folium.Map(location=map_center, zoom_start=15, tiles="CartoDB Positron")

# Add Draw plugin
draw = Draw(
    export=True,
    filename="rooftop.geojson",
    draw_options={"polyline": False, "circle": False, "circlemarker": False, "marker": False, "polygon": True, "rectangle": True},
    edit_options={"edit": True}
)
draw.add_to(m)

map_data = st_folium(m, width=700, height=500)

# ------------------------
# Handle user-drawn polygon
# ------------------------
rooftop_area = None
panels_fit = None
poly = None

if map_data and map_data.get("all_drawings"):
    drawings = map_data["all_drawings"]
    if drawings:
        rooftop_polygon = drawings[-1]["geometry"]["coordinates"]
        if isinstance(rooftop_polygon[0][0], (list, tuple)):
            rooftop_polygon = rooftop_polygon[0]

        poly = np.array(rooftop_polygon)
        lons = poly[:,0]
        lats = poly[:,1]

        # Approximate area in m²
        lat_span = (lats.max() - lats.min()) * 111000
        lon_span = (lons.max() - lons.min()) * 111000 * np.cos(np.radians(lats.mean()))
        rooftop_area = abs(lat_span * lon_span)
        panel_area = 1.7 * 1.0  # m² per panel
        panels_fit = int(rooftop_area / panel_area)

        st.success(f"✅ Rooftop polygon drawn! Estimated area: {rooftop_area:.2f} m², Panels fit: {panels_fit}")

# ------------------------
# User Inputs for Solar Calculation
# ------------------------
st.sidebar.header("System & Financial Parameters")
panel_eff = st.sidebar.slider("Panel Efficiency (%)", 10, 23, 18) / 100
coverage = st.sidebar.slider("Coverage Fraction of Rooftop", 10, 100, 80) / 100
tilt_deg = st.sidebar.slider("Tilt Angle (deg)", 0, 45, 20)
electricity_rate = st.sidebar.number_input("Electricity Rate (₹/kWh)", value=7.0)
subsidy_pct = st.sidebar.slider("Subsidy (%)", 0, 100, 0)

latitude_val = st.sidebar.number_input("Latitude", value=20.3)
longitude_val = st.sidebar.number_input("Longitude", value=85.8)

# ------------------------
# NASA POWER GHI fetch
# ------------------------
def fetch_nasa_ghi(lat, lon):
    url = f"https://power.larc.nasa.gov/api/temporal/climatology/point?parameters=ALLSKY_SFC_SW_DWN&community=RE&longitude={lon}&latitude={lat}&format=JSON"
    try:
        r = requests.get(url, timeout=15)
        data = r.json()
        ghi_monthly = {k: float(v) for k,v in data['properties']['parameter']['ALLSKY_SFC_SW_DWN'].items()}
        ghi_avg = np.mean(list(ghi_monthly.values()))
        return ghi_avg, ghi_monthly
    except:
        fallback = {f"{m:02d}":5.0 for m in range(1,13)}
        return 5.0, fallback

# ------------------------
# Solar System Calculation
# ------------------------
def calc_system(area_m2, ghi_avg, coverage, panel_eff, tilt_deg):
    usable_area = area_m2 * coverage
    capacity_kw = usable_area * 0.2  # kW
    tilt_factor = max(0.5, math.cos(math.radians(tilt_deg)))
    monthly_kwh = usable_area * ghi_avg * panel_eff * 30 * tilt_factor
    return usable_area, capacity_kw, monthly_kwh, tilt_factor

def monthly_forecast(area_m2, ghi_monthly, panel_eff, coverage, tilt_deg):
    days_in_month = [31,28,31,30,31,30,31,31,30,31,30,31]
    forecast = []
    tilt_factor = max(0.5, math.cos(math.radians(tilt_deg)))
    for i, m in enumerate(range(1,13)):
        ghi = ghi_monthly.get(f"{m:02d}",5.0)
        forecast.append(area_m2 * coverage * ghi * panel_eff * days_in_month[i] * tilt_factor)
    return forecast

# ------------------------
# Run Analysis Button
# ------------------------
if st.button("Run Analysis") and rooftop_area is not None:
    ghi_avg, ghi_monthly = fetch_nasa_ghi(latitude_val, longitude_val)
    usable_area, system_kw, monthly_kwh, tilt_factor = calc_system(rooftop_area, ghi_avg, coverage, panel_eff, tilt_deg)
    monthly_out = monthly_forecast(rooftop_area, ghi_monthly, panel_eff, coverage, tilt_deg)

    gross_monthly_value = monthly_kwh * electricity_rate
    subsidy_value = gross_monthly_value * (subsidy_pct/100.0)
    net_monthly_value = gross_monthly_value + subsidy_value

    st.subheader("🔆 System Estimate")
    st.write(f"Usable Rooftop Area: {usable_area:.2f} m²")
    st.write(f"Estimated System Size: {system_kw:.2f} kW")
    st.write(f"Estimated Monthly Production: {monthly_kwh:.2f} kWh")
    st.write(f"Tilt Correction Factor: {tilt_factor:.2f}")
    st.write(f"Gross Monthly Value: ₹{gross_monthly_value:.2f}")
    st.write(f"Subsidy Value: ₹{subsidy_value:.2f}")
    st.write(f"Net Monthly Value: ₹{net_monthly_value:.2f}")

    # Monthly Chart
    st.subheader("📈 Monthly Solar Output Forecast (kWh)")
    fig, ax = plt.subplots(figsize=(10,4))
    ax.plot(range(1,13), monthly_out, marker='o', color='orange')
    ax.set_xlabel("Month")
    ax.set_ylabel("kWh")
    ax.set_title("Monthly Solar Output")
    ax.grid(True)
    st.pyplot(fig)

    # Panel Layout Visualization (simple grid)
    st.subheader("🟨 Panel Layout Preview")
    fig2, ax2 = plt.subplots(figsize=(6,6))
    # Show polygon shape
    poly_mask = np.zeros((100,100))
    for i in range(0,100,10):
        for j in range(0,100,10):
            poly_mask[i,j] = 1
    ax2.imshow(poly_mask, cmap='YlOrBr', alpha=0.8)
    ax2.set_axis_off()
    st.pyplot(fig2)

    # PDF Generation
    if st.button("📄 Generate PDF Report"):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0,10,"Solar Mapping & Recommendation Report", ln=True, align="C")
        pdf.ln(5)
        pdf.set_font("Arial", size=12)
        pdf.multi_cell(0, 6,
            f"Location: {latitude_val}, {longitude_val}\n"
            f"Estimated Rooftop Area: {rooftop_area:.2f} m²\n"
            f"Usable Area (Coverage): {usable_area:.2f} m²\n"
            f"Estimated System Size: {system_kw:.2f} kW\n"
            f"Estimated Monthly Production: {monthly_kwh:.2f} kWh\n"
            f"Gross Monthly Value: ₹{gross_monthly_value:.2f}\n"
            f"Subsidy: ₹{subsidy_value:.2f}\n"
            f"Net Monthly Value: ₹{net_monthly_value:.2f}\n"
        )
        pdf.output("solar_report.pdf")
        st.success("PDF report generated! ✅")
        st.markdown("[Download PDF](solar_report.pdf)")

        st_folium(m, width=700, height=500)

