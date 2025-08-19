import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
import matplotlib.pyplot as plt
import random

st.set_page_config(page_title="Solar Mapping App", layout="wide")
st.title("☀️ Solar Mapping Recommendation System")

# Sidebar inputs
st.sidebar.header("User Input")
location = st.sidebar.text_input("Enter Location (City)", "New York")
rooftop_area = st.sidebar.number_input("Rooftop Area (sq. meters)", 50, 1000, 200)
latitude = st.sidebar.number_input("Latitude", -90.0, 90.0, 40.7128)
longitude = st.sidebar.number_input("Longitude", -180.0, 180.0, -74.0060)

# Solar calculations
panel_area = 1.6
panels_fit = rooftop_area // panel_area
system_capacity = panels_fit * 0.4
annual_output = round(system_capacity * 1200, 2)
install_cost = round(system_capacity * 1000, 2)
annual_savings = round(annual_output * 0.1, 2)
payback_period = round(install_cost / (annual_savings + 1), 2)
suitability = "✅ Suitable" if annual_output > 5000 else "⚠️ Not Highly Suitable"

# Metrics
st.subheader("📊 Solar Installation Summary")
col1, col2, col3 = st.columns(3)
col1.metric("Panels Fit", int(panels_fit))
col2.metric("System Capacity (kW)", system_capacity)
col3.metric("Annual Solar Output (kWh)", annual_output)

col4, col5, col6 = st.columns(3)
col4.metric("Installation Cost ($)", install_cost)
col5.metric("Annual Savings ($)", annual_savings)
col6.metric("Payback Period (Years)", payback_period)

st.subheader(f"Sustainability Score: {suitability}")

# Monthly forecast
st.subheader("📈 Monthly Solar Output Forecast")
months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
forecast = [annual_output/12 + random.randint(-100,100) for _ in months]
df = pd.DataFrame({"Month": months, "Output (kWh)": forecast})
st.bar_chart(df.set_index("Month"))

# Map
st.subheader("🗺️ Location Map")
m = folium.Map(location=[latitude, longitude], zoom_start=13)
folium.Marker([latitude, longitude], popup="Selected Location").add_to(m)
st_folium(m, width=700, height=500)

# Simple chatbot
st.subheader("💬 Chatbot Assistant")
user_q = st.text_input("Ask me anything about solar installation:")
if user_q:
    if "cost" in user_q.lower():
        st.write(f"The estimated installation cost is **${install_cost}**.")
    elif "savings" in user_q.lower():
        st.write(f"You can save approximately **${annual_savings} per year**.")
    elif "panels" in user_q.lower():
        st.write(f"Your rooftop can fit around **{int(panels_fit)} panels**.")
    else:
        st.write("I recommend consulting a local solar provider for exact details.")
