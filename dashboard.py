import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Dashboard", layout="wide")

st.title("Sales Dashboard")

# Sample Data
data = {
    "Category": ["Product A", "Product B", "Product C", "Product D"],
    "Sales": [400, 600, 300, 500]
}
df = pd.DataFrame(data)

# Layout
col1, col2 = st.columns(2)

with col1:
    # Pie Chart
    st.subheader("Sales Distribution")
    fig_pie = px.pie(df, names="Category", values="Sales", title="Sales Share")
    st.plotly_chart(fig_pie, use_container_width=True)

with col2:
    # Bar Chart
    st.subheader("Sales Comparison")
    fig_bar = px.bar(df, x="Category", y="Sales", title="Sales by Category")
    st.plotly_chart(fig_bar, use_container_width=True)

# Line Chart (Full Width)
st.subheader("Sales Trend Over Time")
time_data = {
    "Month": ["Jan", "Feb", "Mar", "Apr", "May"],
    "Sales": [300, 450, 500, 550, 600]
}
df_time = pd.DataFrame(time_data)

fig_line = px.line(df_time, x="Month", y="Sales", title="Sales Over Time", markers=True)
st.plotly_chart(fig_line, use_container_width=True)
