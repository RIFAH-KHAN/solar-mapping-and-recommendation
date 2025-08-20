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

# --- Interactive Map for Rooftop Polygon Drawing ---
st.subheader("Draw Your Rooftop Boundary")

# Create map (satellite view)
m = folium.Map(location=[20.93, 82.0], zoom_start=6, tiles="CartoDB Positron")

# Add draw tools (polygon + rectangle)
draw = Draw(
    export=True,
    filename="data.geojson",
    draw_options={
        "polyline": False,
        "circle": False,
        "circlemarker": False,
        "marker": False,
        "polygon": True,
        "rectangle": True,
    },
    edit_options={"edit": True}
)
draw.add_to(m)

# Display map in Streamlit
map_data = st_folium(m, width=700, height=500)

# If user has drawn something
if map_data and map_data.get("all_drawings"):
    drawings = map_data["all_drawings"]
    if drawings:
        # Extract last drawn shape
        rooftop_polygon = drawings[-1]["geometry"]["coordinates"]

        # Handle Polygon or MultiPolygon
        if isinstance(rooftop_polygon[0][0], (list, tuple)):
            rooftop_polygon = rooftop_polygon[0]  # take outer ring

        st.success("✅ Rooftop polygon drawn!")

        # Show polygon coordinates
        st.write("Polygon Coordinates (lon, lat):")
        st.write(rooftop_polygon)

        # Convert into numpy array
        poly = np.array(rooftop_polygon)

        # Extract lon/lat
        lons = poly[:, 0]
        lats = poly[:, 1]

        # Compute approximate area (rough estimate in m²)
        # Here we use a bounding box approximation
        lat_span = (lats.max() - lats.min()) * 111000  # meters per degree latitude
        lon_span = (lons.max() - lons.min()) * 111000 * np.cos(np.radians(lats.mean()))
        rooftop_area = abs(lat_span * lon_span)

        st.write(f"Estimated Rooftop Area: **{rooftop_area:.2f} m²**")

        # Estimate panels fit
        panel_area = 1.7 * 1.0  # m² per panel
        panels_fit = int(rooftop_area / panel_area)

        st.write(f"Estimated Panels Fit: **{panels_fit} panels**")

        # Add the polygon back on the map for visualization
        folium.Polygon(
            locations=[(lat, lon) for lon, lat in rooftop_polygon],
            color="blue",
            fill=True,
            fill_opacity=0.3,
        ).add_to(m)

        st_folium(m, width=700, height=500)
