import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import pydeck as pdk
from datetime import datetime, timedelta

# ---------------------------------------------------------
# 1. Page Configuration
# ---------------------------------------------------------
st.set_page_config(
    page_title="Krishi-Mitra Ops",
    page_icon="❇️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------
# 2. "Vibe Coded" Custom CSS Injection
# ---------------------------------------------------------
st.markdown("""
<style>
    /* Import modern typography */
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }
    
    /* Hide default Streamlit branding and header */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Global background tinting for a deeper dark mode */
    .stApp {
        background-color: #0B0F19;
    }
    
    /* Sleek Metric Cards (Glassmorphism + Neon accents) */
    div[data-testid="metric-container"] {
        background: linear-gradient(145deg, #111827 0%, #1E293B 100%);
        border: 1px solid #334155;
        padding: 20px;
        border-radius: 16px;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    div[data-testid="metric-container"]:hover {
        transform: translateY(-2px);
        border-color: #10B981;
    }
    
    /* Target the metric labels */
    div[data-testid="metric-container"] label {
        color: #94A3B8 !important;
        font-weight: 500;
        font-size: 0.95rem;
    }
    
    /* Target the metric values */
    div[data-testid="metric-container"] div[data-testid="stMetricValue"] {
        color: #F8FAFC !important;
        font-weight: 700;
        font-size: 2.2rem;
    }

    /* Custom Pill-Style Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 12px;
        background-color: transparent;
        padding-bottom: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #1E293B;
        border-radius: 8px;
        border: 1px solid #334155;
        color: #94A3B8;
        padding: 10px 20px;
        transition: all 0.2s ease;
    }
    .stTabs [data-baseweb="tab"]:hover {
        color: #F8FAFC;
        border-color: #475569;
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background-color: #10B981;
        border-color: #10B981;
        color: #022C22;
        font-weight: 600;
    }
    
    /* Clean up the sidebar */
    [data-testid="stSidebar"] {
        background-color: #0F172A;
        border-right: 1px solid #1E293B;
    }
    
    /* Custom Dataframe styling */
    [data-testid="stDataFrame"] {
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid #334155;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 3. Sidebar UI
# ---------------------------------------------------------
st.sidebar.markdown("<h2 style='color: #10B981; font-weight: 700; letter-spacing: -0.5px;'>❇️ Krishi-Mitra</h2>", unsafe_allow_html=True)
st.sidebar.caption("v2.0 • Production Telemetry")
st.sidebar.markdown("<br>", unsafe_allow_html=True)

st.sidebar.markdown("**📡 Infrastructure**")
st.sidebar.markdown("`Render API` :green[● Online]")
st.sidebar.markdown("`Uptime Monitor` :green[● Polling]")

st.sidebar.markdown("<br>", unsafe_allow_html=True)
st.sidebar.markdown("**💬 Twilio I/O Pipeline**")
twilio_sent_today = 38
twilio_limit = 50
st.sidebar.progress(twilio_sent_today / twilio_limit)
st.sidebar.caption(f"<span style='color:#94A3B8'>Rolling 24h:</span> **{twilio_sent_today}/{twilio_limit}**", unsafe_allow_html=True)

# ---------------------------------------------------------
# 4. Synthetic Telemetry Data
# ---------------------------------------------------------
@st.cache_data
def load_telemetry_data():
    np.random.seed(42)
    locations = [
        {"city": "Nashik", "lat": 19.9975, "lon": 73.7898, "state": "MH"},
        {"city": "Pune", "lat": 18.5204, "lon": 73.8567, "state": "MH"},
        {"city": "Nagpur", "lat": 21.1458, "lon": 79.0882, "state": "MH"},
        {"city": "Kolhapur", "lat": 16.7050, "lon": 74.2433, "state": "MH"},
        {"city": "Ludhiana", "lat": 30.9010, "lon": 75.8573, "state": "PB"},
    ]
    crops = ["Rice (Paddy)", "Tomato", "Cotton", "Onion", "Sugarcane"]
    diseases = ["Early Blight", "Yellow Stem Borer", "Healthy", "Zinc Deficiency", "Healthy"]
    modalities = ["Voice Note", "Image (Vision)", "Text", "Location Pin"]
    
    records = []
    base_time = datetime.now()
    
    for i in range(140):
        loc = np.random.choice(locations)
        mod = np.random.choice(modalities, p=[0.40, 0.30, 0.20, 0.10])
        conf = round(float(np.random.uniform(0.70, 0.99)), 2)
        
        records.append({
            "id": f"KM-{1000 + i}",
            "time": (base_time - timedelta(minutes=int(i * 11))).strftime("%H:%M"),
            "farmer": f"+91 {np.random.randint(70000, 99999)}*****",
            "type": mod,
            "crop": np.random.choice(crops),
            "region": loc["city"],
            "lat": loc["lat"] + np.random.normal(0, 0.05),
            "lon": loc["lon"] + np.random.normal(0, 0.05),
            "finding": np.random.choice(diseases),
            "conf": conf,
            "latency": round(float(np.random.uniform(0.8, 2.5)), 2),
            "status": "Review Required" if conf < 0.78 else "Auto-Resolved"
        })
    return pd.DataFrame(records)

df = load_telemetry_data()

# ---------------------------------------------------------
# 5. Header & Metric Row
# ---------------------------------------------------------
st.markdown("<h1 style='font-weight: 700; font-size: 2.5rem; letter-spacing: -1px; margin-bottom: 0;'>Command Center</h1>", unsafe_allow_html=True)
st.markdown("<p style='color: #64748B; font-size: 1.1rem; margin-bottom: 2rem;'>Real-time AI diagnostics and network observability.</p>", unsafe_allow_html=True)

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.metric("Total Inbound", f"{len(df)}", "+24 today")
with col2:
    st.metric("Active Nodes", "84", "+6")
with col3:
    st.metric("Avg Latency", "1.6s", "-0.2s")
with col4:
    st.metric("Vision Confidence", "93.4%", "+1.2%")
with col5:
    flagged = len(df[df['status'] == 'Review Required'])
    st.metric("Pending Review", flagged, f"{flagged} unread", delta_color="inverse")

st.markdown("<br>", unsafe_allow_html=True)

# ---------------------------------------------------------
# 6. Content Tabs
# ---------------------------------------------------------
t_feed, t_map, t_analytics, t_hitl = st.tabs([
    "Live Feed", "Threat Map", "Analytics", "HITL Override"
])

# Customize Plotly global layout for the "vibe"
def apply_chart_vibe(fig):
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Outfit", color="#94A3B8"),
        margin=dict(t=40, l=0, r=0, b=0),
        xaxis=dict(showgrid=False, zeroline=False),
        yaxis=dict(showgrid=True, gridcolor="#1E293B", zeroline=False)
    )
    return fig

# --- TAB 1: Live Feed ---
with t_feed:
    st.markdown("### Streaming Webhooks")
    
    # Sleeker dataframe configuration
    st.dataframe(
        df[["time", "id", "farmer", "type", "crop", "region", "finding", "conf", "status"]],
        use_container_width=True,
        hide_index=True,
        column_config={
            "conf": st.column_config.ProgressColumn("Confidence", min_value=0, max_value=1, format="%.2f"),
            "status": st.column_config.TextColumn("Status")
        }
    )

# --- TAB 2: Threat Map ---
with t_map:
    st.markdown("### Live Geospatial Diagnostics")
    
    # Neon green for healthy, Hot pink for diseases
    layer = pdk.Layer(
        "ScatterplotLayer",
        df,
        get_position=["lon", "lat"],
        get_color="[244, 63, 94, 200]" if "Blight" in df["finding"] or "Borer" in df["finding"] else "[16, 185, 129, 200]",
        get_radius=15000,
        pickable=True,
        auto_highlight=True,
    )
    
    view_state = pdk.ViewState(latitude=19.7515, longitude=75.7139, zoom=5.8, pitch=35)
    
    r = pdk.Deck(
        layers=[layer], 
        initial_view_state=view_state,
        tooltip={"text": "{crop} in {region}\nDiagnosis: {finding}\nConfidence: {conf}"},
        map_style="mapbox://styles/mapbox/dark-v11" # Deeper dark map
    )
    st.pydeck_chart(r)

# --- TAB 3: Analytics ---
with t_analytics:
    c1, c2 = st.columns(2)
    with c1:
        fig_mod = px.pie(df, names="type", title="Ingestion by Modality", hole=0.6, 
                         color_discrete_sequence=["#10B981", "#3B82F6", "#F59E0B", "#8B5CF6"])
        st.plotly_chart(apply_chart_vibe(fig_mod), use_container_width=True)
    with c2:
        crop_counts = df['crop'].value_counts().reset_index()
        fig_crops = px.bar(crop_counts, x='crop', y='count', title="Query Volume by Crop",
                           color_discrete_sequence=["#3B82F6"])
        st.plotly_chart(apply_chart_vibe(fig_crops), use_container_width=True)

# --- TAB 4: HITL Override ---
with t_hitl:
    st.markdown("### Manual Agronomist Triage")
    flagged_df = df[df["status"] == "Review Required"].reset_index(drop=True)
    
    if len(flagged_df) == 0:
        st.success("All AI inferences cleared with high confidence.")
    else:
        for idx, row in flagged_df.head(3).iterrows():
            with st.container():
                st.markdown(f"""
                <div style='background-color: #1E293B; border-left: 4px solid #F59E0B; padding: 15px; border-radius: 4px; margin-bottom: 10px;'>
                    <strong style='color:#F8FAFC;'>Case {row['id']}</strong> | {row['crop']} in {row['region']} <br>
                    <span style='color:#94A3B8;'>AI suspected </span> <b>{row['finding']}</b> <span style='color:#94A3B8;'>but confidence was only</span> <b>{int(row['conf']*100)}%</b>.
                </div>
                """, unsafe_allow_html=True)
                
                c_a, c_b = st.columns([3, 1])
                with c_a:
                    st.text_input("Final Diagnosis & Treatment Plan", value=f"Confirmed {row['finding']}. Apply recommended treatment.", key=f"t_{idx}")
                with c_b:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("Dispatch WhatsApp", key=f"b_{idx}", use_container_width=True):
                        st.toast(f"Override sent to {row['farmer']}")
                st.markdown("---")
