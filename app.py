# app.py
# app.py
import streamlit as st
from streamlit_folium import st_folium
import folium
from folium import plugins
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
from io import BytesIO
from fpdf import FPDF
import math

# -----------------------------
# App Title and Slogan
# -----------------------------
st.set_page_config(page_title="Solar Mapping & Recommendation", layout="wide")
st.title("☀ Solar Mapping & Recommendation System")
st.subheader("Empowering rooftops, one panel at a time!")

st.markdown("""
Enhance your rooftop potential! Draw your rooftop polygon on the map and see your solar energy output forecast instantly.
""")

# -----------------------------
# Sidebar Inputs
# -----------------------------
st.sidebar.header("Scenario / Finance")
panel_eff = st.sidebar.slider("Panel Efficiency", 0.1, 0.23, 0.18, 0.01)
coverage = st.sidebar.slider("Coverage Fraction", 0.1, 1.0, 0.8, 0.05)
tilt_deg = st.sidebar.slider("Panel Tilt (deg)", 0, 45, 20)
electricity_rate = st.sidebar.number_input("₹ / kWh", value=7.0)
subsidy_pct = st.sidebar.slider("Subsidy %", 0, 100, 0)

# -----------------------------
# Map for drawing rooftop polygon
# -----------------------------
st.subheader("Draw Rooftop Polygon")
default_location = [20.3, 85.8]  # Raipur approx
m = folium.Map(location=default_location, zoom_start=18)

draw = plugins.Draw(export=True)
draw.add_to(m)

st.markdown("**Instructions:** Use the polygon tool to draw your rooftop. Click 'Edit' to adjust. Once done, click 'Export' and copy GeoJSON.")
geojson_input = st.text_area("Paste polygon GeoJSON here:")

map_data = st_folium(m, width=700, height=500)

# -----------------------------
# Helper functions
# -----------------------------
def polygon_area_m2(polygon_coords):
    """Calculate approximate area in m² using simple planar approximation."""
    x = np.array([c[0] for c in polygon_coords])
    y = np.array([c[1] for c in polygon_coords])
    # Approximate conversion assuming small area (lat/lon -> meters)
    lat_mean = np.mean(y)
    lon_to_m = 111320 * np.cos(math.radians(lat_mean))
    lat_to_m = 110540
    xm = (x - x[0]) * lon_to_m
    ym = (y - y[0]) * lat_to_m
    # shoelace formula
    return 0.5 * abs(np.dot(xm, np.roll(ym, 1)) - np.dot(ym, np.roll(xm,1)))

def tilt_loss_factor(tilt_deg, latitude):
    optimal = abs(latitude)
    loss = math.cos(math.radians(tilt_deg - optimal))
    return max(0.5, loss)

def monthly_forecast(area_m2, ghi_monthly, panel_eff, coverage, tilt_deg, latitude):
    days_in_month = [31,28,31,30,31,30,31,31,30,31,30,31]
    out = []
    tilt_factor = tilt_loss_factor(tilt_deg, latitude)
    for i, m in enumerate(range(1,13)):
        ghi = ghi_monthly.get(f"{m:02d}", 5.0)
        monthly = area_m2 * coverage * ghi * panel_eff * tilt_factor * days_in_month[i]
        out.append(monthly)
    return out

# -----------------------------
# Run analysis if GeoJSON provided
# -----------------------------
if geojson_input.strip():
    try:
        import json
        gj = json.loads(geojson_input)
        coords = gj['features'][0]['geometry']['coordinates'][0]  # polygon outer ring
        area_m2 = polygon_area_m2(coords)
        st.success(f"Estimated rooftop area: {area_m2:.2f} m²")

        # Fake monthly GHI for demo
        ghi_monthly = {f"{m:02d}": 5.0 for m in range(1,13)}

        latitude = np.mean([c[1] for c in coords])
        monthly_out = monthly_forecast(area_m2, ghi_monthly, panel_eff, coverage, tilt_deg, latitude)

        st.subheader("Monthly Solar Output Forecast (kWh)")
        st.line_chart(monthly_out)

        # -----------------------------
        # Panel Layout Visualization
        # -----------------------------
        st.subheader("Panel Layout Preview")
        img_size = 400
        panel_px = max(5, int(math.sqrt(1.6)/0.5))  # example panel ~1.6 m², assume 0.5 m/pixel
        canvas = np.zeros((img_size,img_size,3), dtype=np.uint8) + 220
        for i in range(0,img_size,panel_px):
            for j in range(0,img_size,panel_px):
                canvas[i:i+panel_px,j:j+panel_px] = [255,255,0]  # yellow panels
        st.image(canvas, caption="Panel grid preview (hover info not interactive in Streamlit images)", use_column_width=True)

        # -----------------------------
        # PDF Report
        # -----------------------------
        if st.button("Generate PDF Report"):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            pdf.multi_cell(0,6,f"Solar Rooftop Analysis Report\nRooftop area: {area_m2:.2f} m²\nEstimated monthly output (kWh): {monthly_out}")
            pdf.output("solar_report.pdf")
            st.success("PDF saved as solar_report.pdf")

    except Exception as e:
        st.error(f"Error parsing GeoJSON: {e}")

# -----------------------------
# Footer image and slogan
# -----------------------------
st.image("https://www.cleanpng.com/png-solar-panel-sun-energy-photovoltaic-electricity-solar-316485/", width=400)
st.markdown("**Let's make every rooftop a clean energy hub! ☀**")
