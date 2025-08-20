# app.py
# app.py
import streamlit as st
from streamlit_folium import st_folium
import folium
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from fpdf import FPDF
from PIL import Image
import io
import math

# ------------------------
# Page setup
# ------------------------
st.set_page_config(page_title="Solar Mapping & Recommendation",
                   page_icon="☀️", layout="wide")
st.title("☀️ Solar Mapping & Recommendation System")
st.markdown("*Empower your rooftop with clean energy!* 🌱")

# ------------------------
# Sidebar: Input parameters
# ------------------------
st.sidebar.header("Settings")
panel_efficiency = st.sidebar.slider("Panel Efficiency", 0.10, 0.23, 0.18)
coverage = st.sidebar.slider("Coverage fraction", 0.1, 1.0, 0.8)
tilt = st.sidebar.slider("Tilt (degrees)", 0, 45, 20)
elec_rate = st.sidebar.number_input("Electricity rate (₹/kWh)", 1.0, 50.0, 7.0)
subsidy_pct = st.sidebar.slider("Subsidy %", 0, 100, 0)
meters_per_pixel = st.sidebar.number_input("Meters per pixel", 0.1, 5.0, 0.5)

# ------------------------
# Map & Polygon selection
# ------------------------
st.subheader("Step 1: Select Rooftop Area")
m = folium.Map(location=[20.3, 85.8], zoom_start=18)
poly = folium.Polygon(
    locations=[[20.3001,85.8001],[20.3001,85.8002],[20.3002,85.8002],[20.3002,85.8001]],
    color="green",
    fill=True,
    fill_opacity=0.4
)
poly.add_to(m)
# Display interactive map
map_data = st_folium(m, width=700, height=450)

# ------------------------
# Image upload (optional)
# ------------------------
st.subheader("Step 2: Upload rooftop image (optional)")
uploaded_file = st.file_uploader("Choose an image", type=['png','jpg','jpeg'])
if uploaded_file:
    pil_img = Image.open(uploaded_file)
    st.image(pil_img, caption="Uploaded Rooftop Image", use_column_width=True)

# ------------------------
# Compute rooftop area (from polygon)
# ------------------------
st.subheader("Step 3: Compute System Output")
if map_data and "all_drawings" in map_data:
    try:
        poly_coords = map_data["all_drawings"][0]["geometry"]["coordinates"][0]
        poly_array = np.array(poly_coords)
        # Compute centroid
        lat = poly_array[:,1].mean()
        lon = poly_array[:,0].mean()
        # Simple area approximation (meters_per_pixel^2 per pixel)
        num_pixels = len(poly_array)
        area_m2 = num_pixels * meters_per_pixel**2
        st.success(f"Estimated Rooftop Area: {area_m2:.2f} m²")
    except:
        st.warning("Draw a polygon on the map to select rooftop.")

# ------------------------
# Panel layout
# ------------------------
st.subheader("Step 4: Panel Layout Visualization")
if uploaded_file or (map_data and "all_drawings" in map_data):
    # Simple panel grid overlay
    fig, ax = plt.subplots(figsize=(6,6))
    if uploaded_file:
        ax.imshow(pil_img)
        h, w = pil_img.size[1], pil_img.size[0]
    else:
        h = w = 400  # dummy size if no image
    
    panel_px = 20
    kwh_per_panel = 1.2  # sample value per panel
    for r in range(0, h, panel_px):
        for c in range(0, w, panel_px):
            rect = Rectangle((c,r), panel_px, panel_px, linewidth=0.5,
                             edgecolor='yellow', facecolor='yellow', alpha=0.5)
            ax.add_patch(rect)
            ax.text(c+panel_px/2, r+panel_px/2, f"{kwh_per_panel} kWh",
                    color='black', fontsize=6, ha='center', va='center')
    ax.set_axis_off()
    st.pyplot(fig)

# ------------------------
# Monthly forecast chart
# ------------------------
st.subheader("Step 5: Monthly Solar Forecast")
months = list(range(1,13))
monthly_kwh = [area_m2 * coverage * panel_efficiency * 5 * 30 for _ in months] if 'area_m2' in locals() else [0]*12
st.line_chart(monthly_kwh)

# ------------------------
# Generate PDF report
# ------------------------
st.subheader("Step 6: Generate PDF Report")
if st.button("Generate PDF"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(0,10,"Solar Analysis Report", ln=True)
    pdf.cell(0,10,f"Location: {lat:.6f}, {lon:.6f}", ln=True)
    pdf.cell(0,10,f"Rooftop Area: {area_m2:.2f} m²", ln=True)
    pdf.cell(0,10,f"System Efficiency: {panel_efficiency*100:.1f}%", ln=True)
    pdf.cell(0,10,f"Monthly kWh per panel approx: {kwh_per_panel}", ln=True)
    fname = "solar_report.pdf"
    pdf.output(fname)
    with open(fname, "rb") as f:
        st.download_button("Download PDF", f, file_name=fname)

# ------------------------
# Footer
# ------------------------
st.markdown("---")
st.markdown("🌞 *Switch to solar, save money & the planet!* 🌱")
st.image("https://images.unsplash.com/photo-1584270354949-cf9292f2f70b?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=MnwxMTc3M3wwfDF8c2VsZmRlfHx8fHx8fHwxNjkwMDA1MTA0&ixlib=rb-4.0.3&q=80&w=800")
