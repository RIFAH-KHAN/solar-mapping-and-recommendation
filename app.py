import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import folium
from streamlit_folium import st_folium

# --- Sidebar Inputs ---
st.sidebar.header("User Input")
location = st.sidebar.text_input("Enter Location", "Raipur, India")
latitude = st.sidebar.number_input("Latitude", 20.93)
longitude = st.sidebar.number_input("Longitude", 82.0)
rooftop_area = st.sidebar.number_input("Rooftop Area (m²)", 50, 1000, 200)

# Panel assumptions
panel_length = 1.6  # meters
panel_width = 1.0   # meters
panel_area = panel_length * panel_width

# --- Calculations ---
panels_fit = int(rooftop_area // panel_area)
system_capacity = panels_fit * 0.4  # kW, assume 400W per panel
annual_output = system_capacity * 1500  # kWh/year
installation_cost = system_capacity * 60000  # INR
annual_savings = annual_output * 6  # INR
payback_period = installation_cost / annual_savings
suitability = "Highly Suitable" if payback_period < 7 else "Moderately Suitable"

# --- Results ---
st.subheader("Solar Recommendation")
st.write(f"**Location:** {location}")
st.write(f"**Rooftop Area:** {rooftop_area} m²")
st.write(f"**Panels Fit:** {panels_fit}")
st.write(f"**System Capacity:** {system_capacity:.2f} kW")
st.write(f"**Annual Solar Output:** {annual_output:.2f} kWh")
st.write(f"**Installation Cost:** ₹{installation_cost:,.0f}")
st.write(f"**Annual Savings:** ₹{annual_savings:,.0f}")
st.write(f"**Payback Period:** {payback_period:.1f} years")
st.write(f"**Suitability:** {suitability}")

# --- Panel Layout (Grid Diagram) ---
st.subheader("Panel Layout (Grid View)")

cols = int(np.floor(np.sqrt(panels_fit)))
rows = int(np.ceil(panels_fit / cols))

fig, ax = plt.subplots(figsize=(6, 6))
for i in range(rows):
    for j in range(cols):
        idx = i * cols + j
        if idx < panels_fit:
            rect = plt.Rectangle((j*panel_width, i*panel_length),
                                 panel_width, panel_length,
                                 facecolor="skyblue", edgecolor="black")
            ax.add_patch(rect)

ax.set_xlim(0, cols*panel_width)
ax.set_ylim(0, rows*panel_length)
ax.set_aspect('equal')
ax.set_title("Panel Layout on Rooftop (Grid View)")
ax.set_xlabel("Width (m)")
ax.set_ylabel("Length (m)")

st.pyplot(fig)

# --- Folium Map with Panel Overlay ---
st.subheader("Panel Layout on Map")

m = folium.Map(location=[latitude, longitude], zoom_start=20, tiles="OpenStreetMap")

# Create a simple rectangular layout for panels around the chosen lat/lon
# Convert meters to degrees approx (1 deg lat ≈ 111,000 m, lon depends on latitude)
meters_per_degree_lat = 111000
meters_per_degree_lon = 111000 * np.cos(np.radians(latitude))

offset_x = panel_width / meters_per_degree_lon
offset_y = panel_length / meters_per_degree_lat

count = 0
for i in range(rows):
    for j in range(cols):
        if count < panels_fit:
            lat1 = latitude + i * offset_y
            lon1 = longitude + j * offset_x
            lat2 = lat1 + offset_y
            lon2 = lon1 + offset_x
            folium.Rectangle(
                bounds=[[lat1, lon1], [lat2, lon2]],
                color="blue",
                fill=True,
                fill_opacity=0.5
            ).add_to(m)
            count += 1

st_folium(m, width=700, height=500)
