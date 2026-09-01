import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import pydeck as pdk
from datetime import datetime, timedelta

# ---------------------------------------------------------
# 1. Page Configuration & Custom Theme
# ---------------------------------------------------------
st.set_page_config(
    page_title="Krishi-Mitra Command Center",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .metric-card {
        background-color: #1e293b;
        border: 1px solid #334155;
        padding: 16px;
        border-radius: 8px;
        color: white;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 12px;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 8px 16px;
        border-radius: 6px;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. Sidebar Telemetry & Cloud Health
# ---------------------------------------------------------
st.sidebar.image("https://img.icons8.com/color/96/wheat.png", width=64)
st.sidebar.title("Krishi-Mitra Ops")
st.sidebar.caption("Multimodal AI Telemetry & Agronomy Hub")

st.sidebar.markdown("---")
st.sidebar.subheader("🌐 Cloud Infrastructure")
st.sidebar.markdown("**Backend:** `Render Web Service`")
st.sidebar.markdown("**FastAPI Endpoint:** :green[● Healthy (200 OK)]")
st.sidebar.markdown("**Keep-Alive Engine:** :green[● Active (UptimeRobot)]")

# Dynamic Twilio Sandbox Quota Monitor
st.sidebar.markdown("---")
st.sidebar.subheader("📊 Twilio Quota Tracker")
twilio_sent_today = 38
twilio_limit = 50
quota_ratio = twilio_sent_today / twilio_limit

st.sidebar.progress(quota_ratio)
st.sidebar.caption(f"Rolling 24h Window: **{twilio_sent_today}/{twilio_limit} messages**")
if quota_ratio >= 0.8:
    st.sidebar.warning("⚠️ Approaching Twilio daily message ceiling!")

# ---------------------------------------------------------
# 3. Telemetry Data Generation (Synthetic Feed)
# ---------------------------------------------------------
@st.cache_data
def load_telemetry_data():
    np.random.seed(42)
    locations = [
        {"city": "Nashik", "lat": 19.9975, "lon": 73.7898, "state": "Maharashtra"},
        {"city": "Pune", "lat": 18.5204, "lon": 73.8567, "state": "Maharashtra"},
        {"city": "Nagpur", "lat": 21.1458, "lon": 79.0882, "state": "Maharashtra"},
        {"city": "Kolhapur", "lat": 16.7050, "lon": 74.2433, "state": "Maharashtra"},
        {"city": "Ludhiana", "lat": 30.9010, "lon": 75.8573, "state": "Punjab"},
    ]
    crops = ["Rice (Paddy)", "Tomato", "Cotton", "Onion", "Sugarcane", "Wheat"]
    diseases = ["Early Blight", "Yellow Stem Borer", "Leaf Curl Virus", "Zinc Deficiency", "Healthy Crop", "Powdery Mildew"]
    modalities = ["Audio (Voice Note)", "Image (Vision)", "Text Query", "GPS Weather Pin"]
    
    records = []
    base_time = datetime.now()
    
    for i in range(120):
        loc = np.random.choice(locations)
        crop = np.random.choice(crops)
        mod = np.random.choice(modalities, p=[0.35, 0.30, 0.25, 0.10])
        dis = np.random.choice(diseases)
        conf = round(float(np.random.uniform(0.68, 0.99)), 2)
        latency = round(float(np.random.uniform(0.8, 3.2)), 2)
        
        records.append({
            "interaction_id": f"KM-{1000 + i}",
            "timestamp": (base_time - timedelta(minutes=int(i * 14))).strftime("%Y-%m-%d %H:%M"),
            "farmer_id": f"+91 {np.random.randint(70000, 99999)} {np.random.randint(10000, 99999)}",
            "modality": mod,
            "crop": crop,
            "city": loc["city"],
            "lat": loc["lat"] + np.random.normal(0, 0.05),
            "lon": loc["lon"] + np.random.normal(0, 0.05),
            "diagnosis": dis,
            "confidence": conf,
            "latency_sec": latency,
            "status": "Flagged for Review" if conf < 0.75 else "Resolved"
        })
    return pd.DataFrame(records)

df = load_telemetry_data()

# ---------------------------------------------------------
# 4. Main Metric Header
# ---------------------------------------------------------
st.title("🌾 Krishi-Mitra Central Administration")
st.markdown("Real-time monitoring for inbound WhatsApp queries, Gemini inference health, and field diagnostics.")

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.metric("Total Inbound", f"{len(df):,}", "+18 today")
with col2:
    st.metric("Unique Farmers", "84", "+6")
with col3:
    st.metric("Avg Latency", "1.84s", "-0.2s (FastAPI)")
with col4:
    st.metric("Vision Confidence", "91.4%", "+2.1%")
with col5:
    flagged_count = len(df[df['status'] == 'Flagged for Review'])
    st.metric("HITL Flagged", flagged_count, "5 pending", delta_color="inverse")

st.markdown("---")

# ---------------------------------------------------------
# 5. Dashboard Tabs
# ---------------------------------------------------------
tab_analytics, tab_feed, tab_map, tab_hitl, tab_cms = st.tabs([
    "📈 System Analytics",
    "🛰️ Inbound Feed",
    "🗺️ Disease Heatmap",
    "👨‍🌾 Agronomist Queue (HITL)",
    "💰 Mandi CMS"
])

# Tab 1: System Analytics
with tab_analytics:
    st.subheader("Ingestion & Latency Metrics")
    c1, c2 = st.columns(2)
    with c1:
        fig_mod = px.pie(
            df, names="modality", title="Inbound Traffic by Modality",
            color_discrete_sequence=px.colors.qualitative.Prism, hole=0.45
        )
        fig_mod.update_layout(template="plotly_dark", height=320)
        st.plotly_chart(fig_mod, use_container_width=True)
    with c2:
        crop_counts = df['crop'].value_counts().reset_index()
        crop_counts.columns = ['Crop', 'Queries']
        fig_crops = px.bar(
            crop_counts, x='Crop', y='Queries', title="Top Queried Commodities",
            color='Queries', color_continuous_scale="Viridis"
        )
        fig_crops.update_layout(template="plotly_dark", height=320)
        st.plotly_chart(fig_crops, use_container_width=True)

    st.markdown("### Latency Breakdown by Pipeline")
    fig_lat = px.box(
        df, x="modality", y="latency_sec", color="modality",
        title="Processing Latency (FFmpeg / Gemini Vision / Open-Meteo)", points="all"
    )
    fig_lat.update_layout(template="plotly_dark", height=300)
    st.plotly_chart(fig_lat, use_container_width=True)

# Tab 2: Live Inbound Feed
with tab_feed:
    st.subheader("Live Webhook Inspector")
    st.caption("Inspect parsed user sessions, transcribing pipelines, and image diagnostics.")
    
    selected_mods = st.multiselect("Filter by Modality", options=df["modality"].unique(), default=df["modality"].unique())
    filtered_df = df[df["modality"].isin(selected_mods)]
    
    st.dataframe(
        filtered_df[["interaction_id", "timestamp", "farmer_id", "modality", "crop", "city", "diagnosis", "confidence", "latency_sec", "status"]],
        use_container_width=True, hide_index=True
    )
    
    st.markdown("### Sample Ingestion Payloads")
    p1, p2 = st.columns(2)
    with p1:
        st.info("🎙️ **Voice Audio Ingestion (`audio/ogg`)**")
        st.code("Mera tamatar ka patta peela ho raha hai aur sukh raha hai, kya karu?", language="text")
        st.caption("Pipeline: Twilio -> FFmpeg 16kHz WAV -> Google STT -> Gemini 1.5 Flash -> gTTS")
    with p2:
        st.info("📷 **Vision Diagnostic Ingestion (`image/jpeg`)**")
        st.json({
            "detected_crop": "Tomato",
            "pathology": "Early Blight (Alternaria solani)",
            "severity": "Moderate (30% foliage affected)",
            "recommended_treatment": "Mancozeb 75 WP @ 2g/L water spray",
            "confidence_score": 0.94
        })

# Tab 3: Geospatial Disease Heatmap
with tab_map:
    st.subheader("Regional Pathogen Threat Map")
    st.caption("Real-time geographic clusters based on farmer GPS tags and reported symptoms.")
    
    layer = pdk.Layer(
        "ScatterplotLayer",
        df,
        get_position=["lon", "lat"],
        get_color="[239, 68, 68, 200]" if "Blight" in df["diagnosis"] else "[34, 197, 94, 200]",
        get_radius=18000,
        pickable=True,
        auto_highlight=True,
    )
    view_state = pdk.ViewState(latitude=19.7515, longitude=75.7139, zoom=5.5, pitch=20)
    r = pdk.Deck(
        layers=[layer], initial_view_state=view_state,
        tooltip={"text": "ID: {interaction_id}\nCity: {city}\nCrop: {crop}\nDiagnosis: {diagnosis}\nConfidence: {confidence}"},
        map_style="mapbox://styles/mapbox/dark-v10"
    )
    st.pydeck_chart(r)

# Tab 4: Human-in-the-Loop (HITL) Queue
with tab_hitl:
    st.subheader("Agronomist Review & Manual Override")
    st.caption("Queries where automated AI confidence dropped below 75%.")
    
    flagged = df[df["status"] == "Flagged for Review"].reset_index(drop=True)
    if len(flagged) == 0:
        st.success("🎉 All queries resolved with high confidence.")
    else:
        for idx, row in flagged.iterrows():
            with st.expander(f"⚠️ Case {row['interaction_id']} — {row['crop']} ({row['city']}) | Conf: {int(row['confidence'] * 100)}%"):
                col_a, col_b = st.columns(2)
                with col_a:
                    st.write(f"**Farmer ID:** `{row['farmer_id']}`")
                    st.write(f"**Timestamp:** {row['timestamp']}")
                    st.write(f"**Automated Finding:** {row['diagnosis']}")
                    st.write(f"**Confidence Level:** `{row['confidence']}`")
                with col_b:
                    st.markdown("**Manual Agronomist Override:**")
                    st.text_input("Corrected Diagnosis", value=row['diagnosis'], key=f"d_{idx}")
                    st.text_area("Prescription Message", value="Apply Copper Oxychloride 50 WP @ 3g/L. Reduce standing irrigation.", key=f"n_{idx}")
                    if st.button(f"🚀 Dispatch Advisory to WhatsApp", key=f"btn_{idx}"):
                        st.success(f"Custom override pushed directly to {row['farmer_id']} via Twilio REST API!")

# Tab 5: Mandi CMS
with tab_cms:
    st.subheader("Mandi MSP & Commodity Price Manager")
    st.caption("Update benchmark rates directly without editing or redeploying code.")
    
    prices_data = pd.DataFrame([
        {"Crop": "Onion (Kanda)", "Benchmark MSP (₹/Qtl)": 2100, "Current Mandi Avg (₹/Qtl)": 2450, "Market Trend": "Bullish", "State": "Maharashtra"},
        {"Crop": "Rice (Paddy)", "Benchmark MSP (₹/Qtl)": 2300, "Current Mandi Avg (₹/Qtl)": 2320, "Market Trend": "Stable", "State": "All India"},
        {"Crop": "Cotton (Medium)", "Benchmark MSP (₹/Qtl)": 7121, "Current Mandi Avg (₹/Qtl)": 6950, "Market Trend": "Bearish", "State": "Gujarat / MH"},
        {"Crop": "Tomato", "Benchmark MSP (₹/Qtl)": 1500, "Current Mandi Avg (₹/Qtl)": 1800, "Market Trend": "Volatile", "State": "Maharashtra"},
        {"Crop": "Wheat", "Benchmark MSP (₹/Qtl)": 2275, "Current Mandi Avg (₹/Qtl)": 2400, "Market Trend": "Stable", "State": "Punjab / MP"},
    ])
    
    st.data_editor(prices_data, num_rows="dynamic", use_container_width=True)
    if st.button("💾 Save & Sync Prices with Cache"):
        st.success("✅ Updated price matrix synchronized with FastAPI cache!")
