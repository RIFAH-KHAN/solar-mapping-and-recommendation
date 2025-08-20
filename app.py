import streamlit as st
from streamlit_folium import st_folium
import folium
from folium import plugins
import numpy as np
from PIL import Image
from io import BytesIO
import math
import json
import plotly.graph_objects as go
from fpdf import FPDF

# -----------------------------
# Page Config
# -----------------------------
st.set_page_config(
    page_title="Solar Mapping & Recommendation",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------
# Background & Title
# -----------------------------
st.markdown(
    """
    <style>
    .stApp {
        background-image: url('https://images.unsplash.com/photo-1581091012184-6a0b84db86d2?ixlib=rb-4.0.3&auto=format&fit=crop&w=1350&q=80');
        background-size: cover;
        background-attachment: fixed;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("☀ Solar Mapping & Recommendation System")
st.markdown("**Turn your rooftop into a clean energy hub!**")

# -----------------------------
# Sidebar Inputs
# -----------------------------
st.sidebar.header("Scenario / Finance Settings")
panel_eff = st.sidebar.slider("Panel Efficiency", 0.1, 0.23, 0.18, 0.01)
coverage = st.sidebar.slider("Coverage Fraction", 0.1, 1.0, 0.8, 0.05)
tilt_deg = st.sidebar.slider("Panel Tilt (deg)", 0, 45, 20)
electricity_rate = st.sidebar.number_input("₹ / kWh", value=7.0)
subsidy_pct = st.sidebar.slider("Subsidy %", 0, 100, 0)

# -----------------------------
# Interactive Rooftop Polygon Map
# -----------------------------
st.subheader("Draw Your Rooftop")
default_location = [20.3, 85.8]  # Raipur approx
m = folium.Map(location=default_location, zoom_start=18)
draw = plugins.Draw(export=True)
draw.add_to(m)
st.markdown("**Instructions:** Draw polygon -> Click export -> Copy GeoJSON")
geojson_input = st.text_area("Paste GeoJSON here:")

st_data = st_folium(m, width=800, height=500)

# -----------------------------
# Helper functions
# -----------------------------
def polygon_area_m2(polygon_coords):
    x = np.array([c[0] for c in polygon_coords])
    y = np.array([c[1] for c in polygon_coords])
    lat_mean = np.mean(y)
    lon_to_m = 111320 * np.cos(math.radians(lat_mean))
    lat_to_m = 110540
    xm = (x - x[0]) * lon_to_m
    ym = (y - y[0]) * lat_to_m
    return 0.5 * abs(np.dot(xm, np.roll(ym, 1)) - np.dot(ym, np.roll(xm,1)))

def tilt_loss_factor(tilt_deg, latitude):
    optimal = abs(latitude)
    loss = math.cos(math.radians(tilt_deg - optimal))
    return max(0.5, loss)

def monthly_forecast(area_m2, panel_eff, coverage, tilt_deg, latitude):
    days_in_month = [31,28,31,30,31,30,31,31,30,31,30,31]
    ghi_monthly = [5.0]*12
    out = []
    tilt_factor = tilt_loss_factor(tilt_deg, latitude)
    for i in range(12):
        monthly = area_m2 * coverage * panel_eff * tilt_factor * days_in_month[i]
        out.append(monthly)
    return out

# -----------------------------
# Run analysis
# -----------------------------
if geojson_input.strip():
    try:
        gj = json.loads(geojson_input)
        coords = gj['features'][0]['geometry']['coordinates'][0]
        area_m2 = polygon_area_m2(coords)
        st.success(f"Estimated rooftop area: {area_m2:.2f} m²")

        latitude = np.mean([c[1] for c in coords])
        monthly_out = monthly_forecast(area_m2, panel_eff, coverage, tilt_deg, latitude)

        # -----------------------------
        # Monthly Forecast Chart
        # -----------------------------
        st.subheader("Monthly Solar Output Forecast (kWh)")
        months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=months, y=monthly_out, mode='lines+markers', name='kWh'))
        fig.update_layout(title="Monthly Forecast", xaxis_title="Month", yaxis_title="kWh")
        st.plotly_chart(fig, use_container_width=True)

        # -----------------------------
        # Panel Layout Visualization with Hover
        # -----------------------------
        st.subheader("Panel Layout Preview")
        panel_rows = int(math.sqrt(area_m2*coverage))
        panel_cols = panel_rows
        kwh_per_panel = int(np.mean(monthly_out)/ (panel_rows*panel_cols) if panel_rows*panel_cols>0 else 0)
        panel_fig = go.Figure()
        for i in range(panel_rows):
            for j in range(panel_cols):
                panel_fig.add_trace(go.Scatter(
                    x=[j], y=[i],
                    mode='markers',
                    marker=dict(size=30,color='yellow'),
                    hovertemplate=f"{kwh_per_panel} kWh per panel"
                ))
        panel_fig.update_layout(
            xaxis=dict(showgrid=False, zeroline=False, visible=False),
            yaxis=dict(showgrid=False, zeroline=False, visible=False),
            title="Hover over panels to see kWh"
        )
        st.plotly_chart(panel_fig, use_container_width=True)

        # -----------------------------
        # PDF Report Generation
        # -----------------------------
        if st.button("Generate PDF Report"):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            pdf.multi_cell(0,6,f"Solar Rooftop Analysis Report\nRooftop area: {area_m2:.2f} m²\nEstimated monthly output (kWh): {monthly_out}")
            pdf.output("solar_report.pdf")
            st.success("PDF saved as solar_report.pdf")

        # -----------------------------
        # Chatbot Assistant
        # -----------------------------
        st.subheader("Ask Our Solar Bot 🌞")
        user_input = st.text_input("Ask a question about solar installation")
        if user_input:
            # Simple rule-based chatbot
            response = "🤖 Chatbot says: "
            if "tilt" in user_input.lower():
                response += "Optimal tilt is approximately your latitude in degrees."
            elif "efficiency" in user_input.lower():
                response += f"Using high-efficiency panels (~{panel_eff*100:.0f}%) improves output."
            elif "area" in user_input.lower():
                response += f"Your rooftop area is estimated at {area_m2:.2f} m²."
            else:
                response += "Every rooftop is unique; using our polygon tool gives best estimates!"
            st.info(response)

    except Exception as e:
        st.error(f"Error parsing GeoJSON: {e}")

# -----------------------------
# Footer Slogan
# -----------------------------
st.markdown("**Let's make every rooftop a clean energy hub! ☀**")

