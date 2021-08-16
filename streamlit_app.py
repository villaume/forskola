"""An example of showing geographic data."""
import requests
import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import pydeck as pdk
import geopandas as gp

# SETTING PAGE CONFIG TO WIDE MODE
st.set_page_config(layout="wide")

# LOADING DATA
DATA_URL = "https://apigw.stockholm.se/NoAuth/VirtualhittaserviceDMZ/Rest/serviceunits"


payload = ""
headers = {
    'Content-Type': "application/json",
}


@st.cache(persist=True)
def load_data():
    batch_size = 100
    querystring = {"filter[servicetype.id]": "2,1", "page[limit]":f"{batch_size}","page[offset]":"0","sort":"name"}
    resp = requests.request("GET", DATA_URL, data=payload, headers=headers,
                            params=querystring).json()
    all_data = []
    total_count = resp['meta']['totalCount']
    all_data.append(resp.get('data', []))
    for i in range(batch_size, total_count, batch_size):
        querystring = {"filter[servicetype.id]":"2,1","page[limit]":f"{batch_size}","page[offset]":f"{i}","sort":"name"}
        resp = requests.request("GET", DATA_URL, data=payload, headers=headers,
                                params=querystring).json()
        all_data.append(resp.get('data', []))

    return pd.DataFrame([item for sublist in all_data for item in sublist])


def unnest_data(df):
    attributes = pd.json_normalize(df['attributes'])
    relationships = pd.json_normalize(df['relationships'])
    links = pd.json_normalize(df['links'])

    return pd.concat([df[['id']], attributes, relationships, links], axis=1)


def change_coord_system(df, x, y):
    gdf = gp.GeoDataFrame(df,
                          geometry=gp.points_from_xy(df[x], df[y]))
    # coordinates returned was in SWEREF99 18 00
    gdf = gdf.set_crs("EPSG:3011")
    gdf_wgs84 = gdf.to_crs("EPSG:4326")
    gdf_wgs84["lon"] = gdf_wgs84.geometry.x
    gdf_wgs84["lat"] = gdf_wgs84.geometry.y
    gdf_wgs84 = gdf_wgs84.drop('geometry', axis=1)
    return pd.DataFrame(gdf_wgs84)


data = load_data()
unnested_data = unnest_data(data)
remapped = change_coord_system(unnested_data, 'location.east', 'location.north')
# CREATING FUNCTION FOR MAPS


def map(data, lat, lon, zoom):
    st.write(pdk.Deck(
        map_style="mapbox://styles/mapbox/light-v9",
        initial_view_state={
            "latitude": lat,
            "longitude": lon,
            "zoom": zoom,
            "pitch": 50,
        },
        layers=[
            pdk.Layer(
                "HexagonLayer",
                data=data[['lon', 'lat']],
                get_position=["lon", "lat"],
                radius=100,
                elevation_scale=4,
                elevation_range=[0, 1000],
                pickable=True,
                extruded=True,
            ),
        ]
    ))


# LAYING OUT THE TOP SECTION OF THE APP
row1_1, row1_2 = st.columns((2,3))

with row1_1:
    st.title("Forskolor i Stockholm")
    hour_selected = st.slider("Select something", 0, 23)

with row1_2:
    st.write(
    """
    ##
    Forskolor i Stockholm.
    """)

# FILTERING DATA BY HOUR SELECTED

# LAYING OUT THE MIDDLE SECTION OF THE APP WITH THE MAPS
row2_1, row2_2, row2_3, row2_4 = st.columns((2,1,1,1))

midpoint = (np.average(remapped["lat"]), np.average(remapped["lon"]))

with row2_1:
    st.write("**Skolor**")
    map(remapped, midpoint[0], midpoint[1], 11)
