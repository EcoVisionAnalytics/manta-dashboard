import streamlit as st
import pandas as pd
import pydeck as pdk
import altair as alt
import requests
from datetime import datetime, timedelta
from PIL import Image

# Load data
data_path = "data/manta_data.csv"
df = pd.read_csv(data_path)

# Preprocess
if 'Date' in df.columns:
    df['Date'] = df['Date'].astype(str)
if 'Year ' in df.columns:
    df['Year'] = df['Year '].astype(str).str.strip()

# Page config
st.set_page_config(page_title="Florida Manta Project Dashboard", layout="wide")

# Background image with dim overlay
st.markdown("""
    <style>
    body::before {
        content: "";
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        background-image: url('manta.jpg');
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: fixed;
        background-color: rgba(0, 0, 0, 0.4);
        z-index: -1;
    }
    body {
        background-color: #909090;
        color: white;
    }
    .stApp {
        background-color: #909090;
    }
    .st-bb, .st-bc, .st-cq, .st-cn, .st-cp {
        background-color: #7491ab !important;
        color: white !important;
    }
    .stTabs [data-baseweb="tab"] {
        font-size: 1.5rem;
        padding: 12px 20px;
        background-color: #2297fd !important;
        color: white !important;
    }
    </style>
""", unsafe_allow_html=True)

# Logo and header
st.title("Florida Manta Project Dashboard")
logo_path = "MMFLogo.png"
logo = Image.open(logo_path)
col1, col2 = st.columns([9, 1])
with col2:
    st.markdown("<a href='https://marinemegafauna.org' target='_blank'>", unsafe_allow_html=True)
    st.image(logo, width=180)
    st.markdown("</a>", unsafe_allow_html=True)

# Sidebar
with st.sidebar.expander("📘 Instructions for Use", expanded=False):
    st.markdown("""
    **Welcome to the Manta Ray Encounter Dashboard!**

    - Use the **filters below** to explore specific data based on year, sex, and age class.
    - Navigate the **Map** tab to see geolocated encounters.
    - Check the **Visualizations** tab for summary insights.
    - Download filtered data in the **Data View** tab.
    - Upload new data or manually enter encounters in the **Upload Data** tab. ⚠️ Be cautious—these actions alter the dataset.
    - View current tide predictions for select coastal Florida locations under **Current Tides**.

    For questions or support, visit [Marine Megafauna Foundation](https://marinemegafauna.org).
    """)

st.sidebar.header("Filters")
years = sorted(df['Year'].dropna().unique())
sexes = sorted(df['Sex'].dropna().unique())
ages = sorted(df['Age Class'].dropna().unique())

selected_years = st.sidebar.multiselect("Year(s)", years, default=years)
selected_sexes = st.sidebar.multiselect("Sex", sexes, default=sexes)
selected_ages = st.sidebar.multiselect("Age Class", ages, default=ages)

filtered_df = df[
    df['Year'].isin(selected_years) &
    df['Sex'].isin(selected_sexes) &
    df['Age Class'].isin(selected_ages)
]

# Tabs
tabs = st.tabs(["Map", "Visualizations", "Data View", "Upload Data", "Current Tides"])

# --- Data View Tab ---
with tabs[2]:
    st.subheader("Raw Data Table")
    st.dataframe(filtered_df, use_container_width=True)
    st.download_button(
        label="Download Filtered Data as CSV",
        data=filtered_df.to_csv(index=False),
        file_name='filtered_manta_data.csv',
        mime='text/csv'
    )

# --- Upload Tab ---
with tabs[3]:
    st.subheader("Upload New Data")
    uploaded_file = st.file_uploader("Choose a CSV file", type="csv")
    if uploaded_file is not None:
        new_data = pd.read_csv(uploaded_file)
        st.write("Preview of uploaded data:")
        st.dataframe(new_data.head())

        if st.button("Append Uploaded Data to Dataset"):
            st.warning("You're about to append this data to the database. This action is irreversible.")
            new_data.to_csv(data_path, mode='a', index=False, header=False)
            st.success("Data appended. Please reload the app to see updates.")

    st.markdown("---")
    st.subheader("Manual Data Entry")
    st.info("Fill out the form below to manually add a single row to the dataset. Be careful—this alters the database!")

    with st.form("manual_entry_form"):
        st.info("Please fill in **all** columns exactly as listed in the dataset.")
        manual_inputs = {}
        for col in df.columns:
            manual_inputs[col] = st.text_input(col)

        submitted = st.form_submit_button("Submit Entry")
        if submitted:
            new_row = pd.DataFrame([manual_inputs])
            st.warning("You're about to append this row to the database. This action is irreversible.")
            new_row.to_csv(data_path, mode='a', index=False, header=False)
            st.success("Manual entry submitted and saved to dataset.")

# --- Current Tides Tab ---
with tabs[4]:
    st.subheader("Current Tidal Information")
    st.markdown("Live tidal data from key coastal Florida locations:")

    tide_locations = {
        "Miami Beach": "8723214",
        "Pompano Beach": "8722670",
        "Satellite Beach": "8721604"
    }

    today = datetime.utcnow().date()
    begin_date = today.strftime('%Y%m%d')
    end_date = (today + timedelta(days=1)).strftime('%Y%m%d')

    for location, station_id in tide_locations.items():
        st.markdown(f"### {location}")
        url = f"https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?begin_date={begin_date}&end_date={end_date}&station={station_id}&product=predictions&datum=MLLW&units=english&time_zone=lst_ldt&format=json"
        try:
            response = requests.get(url)
            if response.status_code == 200:
                tide_data = response.json()
                if 'predictions' in tide_data:
                    tide_df = pd.DataFrame(tide_data['predictions'])
                    tide_df['t'] = pd.to_datetime(tide_df['t'])
                    tide_df['v'] = tide_df['v'].astype(float)
                    chart = alt.Chart(tide_df).mark_line(point=True).encode(
                        x='t:T',
                        y='v:Q'
                    ).properties(title=f"Tide Predictions for {location}")
                    st.altair_chart(chart, use_container_width=True)
                else:
                    st.warning("No tide predictions found.")
            else:
                st.error(f"Failed to fetch data for {location} (status {response.status_code})")
        except Exception as e:
            st.error(f"Error fetching data for {location}: {e}")

# --- Footer ---
st.markdown("""
    <div style='text-align: center; padding-top: 2rem;'>
        <p style='color: white;'>
            Developed in cooperation with
            <a href='https://ecovisionanalytics.com' target='_blank' style='color: white; text-decoration: underline;'>
                Ecovision Analytics
            </a>. 2025. All rights reserved.
        </p>
    </div>
""", unsafe_allow_html=True)
