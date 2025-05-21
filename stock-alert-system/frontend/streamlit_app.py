
import streamlit as st
import requests

BACKEND_URL = "http://localhost:5000"

st.title("📈 Stock Alert System")

st.subheader("Register Telegram User")
user_id = st.text_input("Telegram User ID")

if st.button("Register User"):
    response = requests.post(f"{BACKEND_URL}/register", json={"user_id": user_id})
    st.success(response.json()["message"])

st.subheader("Send Alert")
alert_msg = st.text_input("Alert Message")

if st.button("Send Alert"):
    response = requests.post(f"{BACKEND_URL}/alerts", json={"message": alert_msg})
    st.success(response.json()["message"])

st.subheader("View All Alerts")
if st.button("Load Alerts"):
    response = requests.get(f"{BACKEND_URL}/alerts")
    alerts = response.json()
    for alert in alerts:
        st.write(f"- {alert['message']}")
