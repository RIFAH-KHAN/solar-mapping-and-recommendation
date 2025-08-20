import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import folium
from streamlit_folium import st_folium

st.set_page_config(layout="wide")

# --- Sidebar Inputs ---
st.sidebar.header("User Input")
location = st.sidebar.text_input("Enter Location Name (Optional)", "Raipur, India")
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

# --- Interactive Map with Rooftop Polygon Drawing ---
st.subheader("Draw Your Rooftop on Map")

# Satellite basemap
m = folium.Map(location=[20.93, 82.0], zoom_start=6, tiles=None)
folium.TileLayer(
    tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    attr="Esri",
    name="Esri Satellite",
    overlay=False,
    control=True
).add_to(m)

# Add drawing tool (polygon)
from folium.plugins import Draw
Draw(export=True, filename="rooftop.geojson", draw_options={"polygon": True, "rectangle": True}).add_to(m)

# Show map in streamlit
map_data = st_folium(m, width=700, height=500)

# Check if user drew a polygon
if map_data and map_data.get("all_drawings"):
    drawings = map_data["all_drawings"]
    if drawings:
        rooftop_polygon = drawings[-1]["geometry"]["coordinates"][0]  # last drawn polygon
        st.success("✅ Rooftop polygon drawn!")

        # Show polygon coords
        st.write("Polygon Coordinates (lat, lon):")
        st.write(rooftop_polygon)

        # Estimate rooftop area (very rough, needs geodesic calculation)
        # Convert polygon into numpy array of lat/lon
        poly = np.array(rooftop_polygon)

        # Approximate meters per degree
        lat = poly[:,1].mean()
        meters_per_deg_lat = 111000
        meters_per_deg_lon = 111000 * np.cos(np.radians(lat))

        # Convert coords into meters
        x = (poly[:,0] - poly[:,0].mean()) * meters_per_deg_lon
        y = (poly[:,1] - poly[:,1].mean()) * meters_per_deg_lat

        # Polygon area using shoelace formula
        area_m2 = 0.5 * np.abs(np.dot(x, np.roll(y,1)) - np.dot(y, np.roll(x,1)))

        st.write(f"Estimated Rooftop Area: {area_m2:.2f} m²")

        # How many panels fit
        panels_fit = int(area_m2 // panel_area)
        st.write(f"Panels Fit: {panels_fit}")

        # Redraw map with panels inside polygon (centered grid)
        m2 = folium.Map(location=[poly[:,1].mean(), poly[:,0].mean()], zoom_start=20, tiles=None)
        folium.TileLayer(
            tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            attr="Esri",
            name="Esri Satellite",
            overlay=False,
            control=True
        ).add_to(m2)

        folium.Polygon(rooftop_polygon, color="cyan", fill=True, fill_opacity=0.3).add_to(m2)

        # Place panels as rectangles (just scatter in bounding box)
        meters_per_degree_lon = meters_per_deg_lon
        meters_per_degree_lat = meters_per_deg_lat

        offset_x = panel_width / meters_per_degree_lon
        offset_y = panel_length / meters_per_degree_lat

        count = 0
        lat_min, lon_min = poly[:,1].min(), poly[:,0].min()

        for i in range(20):  # try filling rows
            for j in range(20):  # try filling cols
                if count < panels_fit:
                    lat1 = lat_min + i * offset_y
                    lon1 = lon_min + j * offset_x
                    lat2 = lat1 + offset_y
                    lon2 = lon1 + offset_x
                    folium.Rectangle(
                        bounds=[[lat1, lon1], [lat2, lon2]],
                        color="yellow", fill=True, fill_opacity=0.5
                    ).add_to(m2)
                    count += 1

        st_folium(m2, width=700, height=500)


if map_data and map_data.get("last_clicked"):
    latitude = map_data["last_clicked"]["lat"]
    longitude = map_data["last_clicked"]["lng"]

    st.success(f"✅ Rooftop selected at: {latitude:.5f}, {longitude:.5f}")

    # Draw panels on rooftop with satellite view
    m2 = folium.Map(location=[latitude, longitude], zoom_start=20, tiles=None)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri",
        name="Esri Satellite",
        overlay=False,
        control=True
    ).add_to(m2)

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
                    color="yellow",
                    fill=True,
                    fill_opacity=0.5
                ).add_to(m2)
                count += 1

    st_folium(m2, width=700, height=500)


if map_data and map_data.get("last_clicked"):
    latitude = map_data["last_clicked"]["lat"]
    longitude = map_data["last_clicked"]["lng"]

    st.success(f"✅ Rooftop selected at: {latitude:.5f}, {longitude:.5f}")

    # Draw panels on selected rooftop
    m2 = folium.Map(location=[latitude, longitude], zoom_start=20, tiles="OpenStreetMap")

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
                ).add_to(m2)
                count += 1

    st_folium(m2, width=700, height=500)




