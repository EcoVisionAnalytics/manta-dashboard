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
    body {background-color:#909090;color:white;}
    .stApp{background-color:#909090;}
    .stTabs [data-baseweb="tab"]{font-size:1.5rem;padding:12px 20px;background:#2297fd!important;color:white!important;}
    .block-container > div > div > div > div{background:#7491ab10;border-radius:10px;padding:1rem;}
    </style>
""", unsafe_allow_html=True)

# Header
st.title("Florida Manta Project Dashboard")
logo = Image.open("MMFLogo.png")
col1, col2 = st.columns([9,1])
with col2:
    st.markdown("<a href='https://marinemegafauna.org' target='_blank'>", unsafe_allow_html=True)
    st.image(logo, width=180)
    st.markdown("</a>", unsafe_allow_html=True)

# Sidebar instructions
with st.sidebar.expander("📘 Instructions for Use", expanded=False):
    st.markdown("""
    **Welcome to the Manta Ray Encounter Dashboard!**
    - Use the **filters** to slice data.
    - Explore **Map**, **Visualizations**, and **Advanced** tabs for insights.
    - Download or upload data in their respective tabs.
    """)

# Sidebar filters
years = sorted(df['Year'].dropna().unique())
sexes = sorted(df['Sex'].dropna().unique())
ages  = sorted(df['Age Class'].dropna().unique())

selected_years = st.sidebar.multiselect("Year(s)", years, default=years)
selected_sexes = st.sidebar.multiselect("Sex", sexes, default=sexes)
selected_ages  = st.sidebar.multiselect("Age Class", ages, default=ages)

filtered_df = df[(df['Year'].isin(selected_years)) & (df['Sex'].isin(selected_sexes)) & (df['Age Class'].isin(selected_ages))]

# Tabs
tabs = st.tabs(["Map", "Visualizations", "Advanced Visualizations", "Data View", "Upload Data", "Current Tides"])

# --- Map Tab ---
with tabs[0]:
    st.subheader("Manta Ray Encounter Map")
    map_df = filtered_df.dropna(subset=['Latitude','Longitude']).astype({'Latitude':float,'Longitude':float})
    st.markdown("<style>.fullscreen-map .stDeckGlJson{height:90vh!important;}</style>", unsafe_allow_html=True)
    with st.container():
        st.markdown("<div class='fullscreen-map'>", unsafe_allow_html=True)
        st.pydeck_chart(pdk.Deck(
            map_style='mapbox://styles/mapbox/satellite-streets-v11',
            initial_view_state=pdk.ViewState(latitude=26.7153,longitude=-80.0534,zoom=10,pitch=50),
            layers=[pdk.Layer('ScatterplotLayer',data=map_df,get_position='[Longitude,Latitude]',get_color='[200,30,0,160]',get_radius=200,pickable=True)],
            tooltip={"html":"<b>Date:</b> {Date}<br/><b>Name:</b> {Name}<br/><b>Sex:</b> {Sex}<br/><b>Age:</b> {Age Class}"}
        ))
        st.markdown("</div>", unsafe_allow_html=True)

# --- Visualizations Tab ---
with tabs[1]:
    st.subheader("Visualizations")
    # Scorecards
    month_opts = sorted(filtered_df['Month'].dropna().unique())
    year_opts  = sorted(filtered_df['Year'].dropna().unique())
    col_m, col_y = st.columns(2)
    sel_months = col_m.multiselect("Filter Scorecards by Month", month_opts, default=month_opts)
    sel_years_sc = col_y.multiselect("Filter Scorecards by Year", year_opts, default=year_opts)
    mdf = filtered_df[(filtered_df['Month'].isin(sel_months)) & (filtered_df['Year'].isin(sel_years_sc))]

    total_enc = len(mdf)
    unique_inds = mdf['Manta Individual'].nunique()
    inj_cnt = mdf['New Injury?'].astype(str).str.lower().isin(['yes','y']).sum()
    if 'Encounter Length (minutes)' in mdf.columns:
        mdf['Encounter Length (minutes)'] = pd.to_numeric(mdf['Encounter Length (minutes)'], errors='coerce')
        mean_len = round(mdf['Encounter Length (minutes)'].mean(),1)
    else:
        mean_len = 'N/A'
    s1,s2,s3,s4 = st.columns(4)
    s1.metric("Total Encounters", total_enc)
    s2.metric("Unique Individuals", unique_inds)
    s3.metric("Mean Encounter Length (min)", mean_len)
    s4.metric("New Injuries", inj_cnt)

    c1,c2 = st.columns(2)
    # Heatmap
    with c1:
        hm = alt.Chart(filtered_df.dropna(subset=['Month','Year'])).mark_rect().encode(
            x=alt.X('Month:N'),
            y=alt.Y('Year:O'),
            color=alt.Color('count():Q', scale=alt.Scale(scheme='blues'))).properties(title="Encounter Frequency by Month and Year", height=300)
        st.altair_chart(hm, use_container_width=True)
        # Depth vs Temp
        scat_df = filtered_df.dropna(subset=['Water Depth (m)','Water Temperature (°C)','Age Class']).copy()
        scat_df['Water Depth (m)'] = pd.to_numeric(scat_df['Water Depth (m)'], errors='coerce')
        scat_df['Water Temperature (°C)'] = pd.to_numeric(scat_df['Water Temperature (°C)'], errors='coerce')
        sc = alt.Chart(scat_df).mark_circle(size=60).encode(
            x='Water Depth (m):Q',
            y=alt.Y('Water Temperature (°C):Q', scale=alt.Scale(domain=[20,35])),
            color='Age Class:N').properties(title="Depth vs Temperature by Age Class", height=300)
        st.altair_chart(sc, use_container_width=True)
    # Right column charts
    with c2:
        inj_df = filtered_df[filtered_df['New Injury?'].astype(str).str.lower().isin(['yes','y'])]
        inj_bar = alt.Chart(inj_df).mark_bar().encode(
            x='Which Pier:N', y='count():Q', color='Which Pier:N').properties(title="Injury Incidence by Pier", height=300)
        st.altair_chart(inj_bar, use_container_width=True)
        wdf = filtered_df.dropna(subset=['Disc Width (m)','Age Class','Sex']).copy()
        wdf['Disc Width (m)'] = pd.to_numeric(wdf['Disc Width (m)'], errors='coerce')
        bp = alt.Chart(wdf).mark_boxplot().encode(x='Age Class:N', y='Disc Width (m):Q', color='Sex:N').properties(title="Disc Width by Age Class and Sex", height=300)
        st.altair_chart(bp, use_container_width=True)

# --- Advanced Visualizations Tab ---
with tabs[2]:
    st.subheader("Advanced Visualizations and Analyses")
    adv_map_df = filtered_df.dropna(subset=['Latitude','Longitude']).astype({'Latitude':float,'Longitude':float})
    # Density heatmap
    if not adv_map_df.empty:
        st.pydeck_chart(pdk.Deck(map_style='mapbox://styles/mapbox/dark-v10',
                                 initial_view_state=pdk.ViewState(latitude=adv_map_df['Latitude'].mean(),longitude=adv_map_df['Longitude'].mean(),zoom=8,pitch=50),
                                 layers=[pdk.Layer("HexagonLayer",data=adv_map_df,get_position='[Longitude,Latitude]',radius=1500,elevation_scale=50,elevation_range=[0,1000],pickable=True,extruded=True)]))
    # Wind rose
    if 'Travel Direction' in filtered_df.columns:
        rd = filtered_df.dropna(subset=['Travel Direction'])
        rd = rd[rd['Travel Direction'].apply(lambda x: str(x).isnumeric())]
        rd['Travel Direction'] = rd['Travel Direction'].astype(int)//30*30
        rose = alt.Chart(rd).mark_arc(innerRadius=20).encode(theta='count():Q', color='Travel Direction:N').properties(title="Travel Direction Frequency")
        st.altair_chart(rose, use_container_width=True)
    # Injury hotspots
    inj_hot = inj_df.dropna(subset=['Latitude','Longitude']).astype({'Latitude':float,'Longitude':float})
    if not inj_hot.empty:
        st.pydeck_chart(pdk.Deck(map_style='mapbox://styles/mapbox/outdoors-v11',
                                 initial_view_state=pdk.ViewState(latitude=inj_hot['Latitude'].mean(),longitude=inj_hot['Longitude'].mean(),zoom=8,pitch=30),
                                 layers=[pdk.Layer('ScatterplotLayer',data=inj_hot,get_position='[Longitude,Latitude]',get_radius=500,get_fill_color='[255,0,0,160]',pickable=True)],
                                 tooltip={"text":"Injury at Pier: {Which Pier}"}))

# --- Data View Tab ---
with tabs[3]:
    st.subheader("Raw Data Table")
    st.dataframe(filtered_df, use_container_width=True)
    st.download_button("Download Filtered Data as CSV", filtered_df.to_csv(index=False), file_name="filtered_manta_data.csv", mime="text/csv")

# --- Upload Data Tab ---
with tabs[4]:
    st.subheader("Upload New Data")
    uploaded_file = st.file_uploader("Choose a CSV file", type="csv")
    if uploaded_file is not None:
        new_data = pd.read_csv(uploaded_file)
        st.dataframe(new_data.head())
        if st.button("Append Uploaded Data to Dataset"):
            st.warning("You're about to append this data to the database. This action is irreversible.")
            new_data.to_csv(data_path, mode='a', index=False, header=False)
            st.success("Data appended. Please reload the app to see updates.")
    st.markdown("---")
    st.subheader("Manual Data Entry")
    with st.form("manual_entry_form"):
        st.info("Fill in all columns exactly as listed.")
        inputs = {col: st.text_input(col) for col in df.columns}
        if st.form_submit_button("Submit Entry"):
            pd.DataFrame([inputs]).to_csv(data_path, mode='a', index=False, header=False)
            st.success("Entry added to dataset.")

# --- Current Tides Tab ---
with tabs[5]:
    st.subheader("Current Tidal Information")
    tide_locations = {"Miami Beach":"8723214","Pompano Beach":"8722670","Satellite Beach":"8721604"}
    today = datetime.utcnow().date()
    begin_date = today.strftime('%Y%m%d'); end_date = (today+timedelta(days=1)).strftime('%Y%m%d')
    for loc, sid in tide_locations.items():
        st.markdown(f"### {loc}")
        url = f"https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?begin_date={begin_date}&end_date={end_date}&station={sid}&product=predictions&datum=MLLW&units=english&time_zone=lst_ldt&format=json"
        try:
            resp = requests.get(url)
            if resp.status_code==200 and 'predictions' in resp.json():
                td = pd.DataFrame(resp.json()['predictions']); td['t']=pd.to_datetime(td['t']); td['v']=td['v'].astype(float)
                st.altair_chart(alt.Chart(td).mark_line(point=True).encode(x='t:T', y='v:Q').properties(title=f"Tide Predictions for {loc}"), use_container_width=True)
            else:
                st.warning("No tide predictions found.")
        except Exception as e:
            st.error(f"Error fetching data for {loc}: {e}")

# --- Footer ---
st.markdown("""
    <div style='text-align:center;padding-top:2rem;'>
        <p style='color:white;'>Developed in cooperation with <a href='https://ecovisionanalytics.com' target='_blank' style='color:white;text-decoration:underline;'>Ecovision Analytics</a>. 2025. All rights reserved.</p>
    </div>
""", unsafe_allow_html=True)
