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
# --- Visualizations Tab ---
with tabs[1]:
    st.subheader("Visualizations")

    # --- Scorecards ---
    st.markdown("""
        <style>
        .block-container > div > div > div > div {
            background-color: #7491ab10;
            border-radius: 10px;
            padding: 1rem;
        }
        </style>
    """, unsafe_allow_html=True)

    month_options = sorted(filtered_df['Month'].dropna().unique())
    year_options = sorted(filtered_df['Year'].dropna().unique())

    col_month, col_year = st.columns(2)
    with col_month:
        selected_months = st.multiselect("Filter Scorecards by Month", month_options, default=month_options)
    with col_year:
        selected_years_scorecard = st.multiselect("Filter Scorecards by Year", year_options, default=year_options)

    month_filtered_df = filtered_df[
        filtered_df['Month'].isin(selected_months) &
        filtered_df['Year'].isin(selected_years_scorecard)
    ]

    score1, score2, score3, score4 = st.columns(4)

    injured_count = month_filtered_df['New Injury?'].astype(str).str.lower().isin(['yes', 'y']).sum()
    unique_individuals = month_filtered_df['Manta Individual'].nunique()
    total_encounters = len(month_filtered_df)

    encounter_col = 'Encounter Length (minutes)'
    if encounter_col in month_filtered_df.columns:
        month_filtered_df[encounter_col] = pd.to_numeric(month_filtered_df[encounter_col], errors='coerce')
        mean_val = month_filtered_df[encounter_col].mean()
        month_filtered_df[encounter_col] = month_filtered_df[encounter_col].fillna(mean_val)
        mean_encounter = round(month_filtered_df[encounter_col].mean(), 1)
    else:
        mean_encounter = 'N/A'

    with score1:
        st.metric(label="Total Encounters", value=total_encounters)
    with score2:
        st.metric(label="Unique Individuals", value=unique_individuals)
    with score3:
        st.metric(label="Mean Encounter Length (min)", value=mean_encounter)
    with score4:
        st.metric(label="New Injuries", value=injured_count)

    col1, col2 = st.columns(2)

    with col1:
        heatmap_data = filtered_df.dropna(subset=['Month', 'Year'])
        heatmap = alt.Chart(heatmap_data).mark_rect().encode(
            x=alt.X('Month:N', title='Month'),
            y=alt.Y('Year:O', title='Year'),
            color=alt.Color('count():Q', scale=alt.Scale(scheme='blues'))
        ).properties(title="Encounter Frequency by Month and Year")
        st.altair_chart(heatmap, use_container_width=True)

        scatter_df = filtered_df.dropna(subset=['Water Depth (m)', 'Water Temperature (°C)', 'Age Class'])
        scatter_df['Water Depth (m)'] = pd.to_numeric(scatter_df['Water Depth (m)'], errors='coerce')
        scatter_df['Water Temperature (°C)'] = pd.to_numeric(scatter_df['Water Temperature (°C)'], errors='coerce')
        scatter = alt.Chart(scatter_df).mark_circle(size=60).encode(
            x='Water Depth (m):Q',
            y='Water Temperature (°C):Q',
            color='Age Class:N',
            tooltip=['Date', 'Name', 'Age Class', 'Water Depth (m)', 'Water Temperature (°C)']
        ).properties(title="Depth vs Temperature by Age Class")
        st.altair_chart(scatter, use_container_width=True)

    with col2:
        injury_df = filtered_df[filtered_df['New Injury?'].notnull() & filtered_df['New Injury?'].str.lower().isin(['yes', 'y'])]
        injury_bar = alt.Chart(injury_df).mark_bar().encode(
            x='Which Pier:N',
            y='count():Q',
            color='Which Pier:N'
        ).properties(title="Injury Incidence by Pier")
        st.altair_chart(injury_bar, use_container_width=True)

        width_df = filtered_df.dropna(subset=['Disc Width (m)', 'Age Class', 'Sex'])
        width_df['Disc Width (m)'] = pd.to_numeric(width_df['Disc Width (m)'], errors='coerce')
        boxplot = alt.Chart(width_df).mark_boxplot().encode(
            x='Age Class:N',
            y='Disc Width (m):Q',
            color='Sex:N'
        ).properties(title="Disc Width by Age Class and Sex")
        st.altair_chart(boxplot, use_container_width=True)

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
