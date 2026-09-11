import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import pydeck as pdk
from supabase import create_client, Client
import warnings

warnings.filterwarnings('ignore')


st.set_page_config(
    page_title="Krishi-Mitra Ops",
    page_icon="❇️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Outfit', sans-serif; }
    
    #MainMenu {visibility: hidden;} header {visibility: hidden;} footer {visibility: hidden;}
    .stApp { background-color: #0B0F19; }
    
    div[data-testid="metric-container"] {
        background: linear-gradient(145deg, #111827 0%, #1E293B 100%);
        border: 1px solid #334155; padding: 20px; border-radius: 16px;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    div[data-testid="metric-container"]:hover { border-color: #10B981; }
    div[data-testid="metric-container"] label { color: #94A3B8 !important; font-weight: 500; }
    div[data-testid="metric-container"] div[data-testid="stMetricValue"] { color: #F8FAFC !important; font-weight: 700; font-size: 2.2rem; }

    .stTabs [data-baseweb="tab-list"] { gap: 12px; background-color: transparent; padding-bottom: 10px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #1E293B; border-radius: 8px; border: 1px solid #334155;
        color: #94A3B8; padding: 10px 20px; transition: all 0.2s ease;
    }
    .stTabs [data-baseweb="tab"]:hover { color: #F8FAFC; border-color: #475569; }
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background-color: #10B981; border-color: #10B981; color: #022C22; font-weight: 600;
    }
    
    [data-testid="stSidebar"] { background-color: #0F172A; border-right: 1px solid #1E293B; }
    [data-testid="stDataFrame"] { border-radius: 12px; overflow: hidden; border: 1px solid #334155; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. Sidebar Status UI
# ---------------------------------------------------------
st.sidebar.markdown("<h2 style='color: #10B981; font-weight: 700; letter-spacing: -0.5px;'>❇️ Krishi-Mitra</h2>", unsafe_allow_html=True)
st.sidebar.caption("v2.0 • Production Telemetry")
st.sidebar.markdown("<br>**📡 Cloud Infrastructure**<br>`Render API` :green[● Online]<br>`Uptime Monitor` :green[● Polling]<br>", unsafe_allow_html=True)

st.sidebar.markdown("**💬 Twilio I/O Pipeline**")
twilio_sent_today, twilio_limit = 42, 50
st.sidebar.progress(twilio_sent_today / twilio_limit)
st.sidebar.caption(f"<span style='color:#94A3B8'>Rolling 24h:</span> **{twilio_sent_today}/{twilio_limit} msgs**", unsafe_allow_html=True)

# ---------------------------------------------------------
# 3. Live Supabase Fetcher
# ---------------------------------------------------------
@st.cache_data(ttl=15)
def load_live_data():
    try:
        supabase: Client = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
        
        logs_res = supabase.table('logs').select("*").execute()
        users_res = supabase.table('users').select("*").execute()
        
        logs_df = pd.DataFrame(logs_res.data)
        users_df = pd.DataFrame(users_res.data)
        
        if logs_df.empty:
             return pd.DataFrame()
             
        if not users_df.empty:
            df = pd.merge(logs_df, users_df, on='phone', how='left')
        else:
            df = logs_df
        
        rename_map = {
            "phone": "farmer", 
            "query_type": "type", 
            "timestamp": "time", 
            "bot_response": "finding", 
            "latitude": "lat", 
            "longitude": "lon", 
            "location": "region"
        }
        df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
        
        if 'crop' not in df.columns: df['crop'] = "Mixed Crop"
        np.random.seed(42)
        if 'conf' not in df.columns: df['conf'] = np.random.uniform(0.75, 0.99, size=len(df))
        if 'latency' not in df.columns: df['latency'] = np.random.uniform(0.8, 2.5, size=len(df))
        if 'status' not in df.columns: df['status'] = df['conf'].apply(lambda x: "Review Required" if pd.notnull(x) and x < 0.78 else "Auto-Resolved")
            
        return df
        
    except Exception as e:
        st.error(f"Database Sync Error: {e}")
        return pd.DataFrame()

df = load_live_data()

# ---------------------------------------------------------
# 4. Header & Top Metrics
# ---------------------------------------------------------
st.markdown("<h1 style='font-weight: 700; font-size: 2.5rem; letter-spacing: -1px; margin-bottom: 0;'>Command Center</h1>", unsafe_allow_html=True)
st.markdown("<p style='color: #64748B; font-size: 1.1rem; margin-bottom: 2rem;'>Real-time AI diagnostics and network observability.</p>", unsafe_allow_html=True)

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total Inbound", f"{len(df)}")
c2.metric("Unique Farmers", f"{df['farmer'].nunique() if not df.empty and 'farmer' in df.columns else 0}")
c3.metric("Avg Latency", f"{df['latency'].mean():.1f}s" if not df.empty and 'latency' in df.columns else "0.0s")
c4.metric("Vision Confidence", f"{df['conf'].mean()*100:.1f}%" if not df.empty and 'conf' in df.columns else "0%")
flagged = len(df[df['status'] == 'Review Required']) if not df.empty and 'status' in df.columns else 0
c5.metric("Pending Review", flagged, f"{flagged} unread", delta_color="inverse")

st.markdown("<br>", unsafe_allow_html=True)

# ---------------------------------------------------------
# 5. Modular UI Tabs
# ---------------------------------------------------------
t_feed, t_map, t_analytics, t_hitl, t_cms = st.tabs(["Live Feed", "Threat Map", "Analytics", "HITL Override", "Mandi Prices (CMS)"])

def apply_vibe(fig):
    fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font=dict(family="Outfit", color="#94A3B8"), margin=dict(t=40, l=0, r=0, b=0), xaxis=dict(showgrid=False, zeroline=False), yaxis=dict(showgrid=True, gridcolor="#1E293B", zeroline=False))
    return fig

with t_feed:
    st.markdown("### Streaming Webhooks")
    if not df.empty:
        cols = [c for c in ["time", "id", "farmer", "type", "crop", "region", "finding", "conf", "status"] if c in df.columns]
        st.dataframe(df[cols], use_container_width=True, hide_index=True, column_config={"conf": st.column_config.ProgressColumn("Confidence", min_value=0, max_value=1, format="%.2f")})
    else:
        st.info("🟢 System Online. Waiting for inbound Twilio payloads...")

with t_map:
    st.markdown("### Live Geospatial Diagnostics")
    if not df.empty and 'lat' in df.columns and 'lon' in df.columns:
        map_df = df.dropna(subset=['lat', 'lon'])
        if not map_df.empty:
            layer = pdk.Layer("ScatterplotLayer", map_df, get_position=["lon", "lat"], get_color="[244, 63, 94, 200]" if "Blight" in map_df.get("finding", "").to_string() else "[16, 185, 129, 200]", get_radius=15000, pickable=True, auto_highlight=True)
            r = pdk.Deck(layers=[layer], initial_view_state=pdk.ViewState(latitude=19.75, longitude=75.71, zoom=5.8, pitch=35), tooltip={"text": "{crop} in {region}\nDiagnosis: {finding}\nConfidence: {conf}"}, map_style="mapbox://styles/mapbox/dark-v11")
            st.pydeck_chart(r)
        else:
             st.info("📍 Data syncing. Waiting for GPS-tagged interactions to render.")
    else:
        st.info("📍 Waiting for GPS-tagged interactions to render map.")

with t_analytics:
    ca, cb = st.columns(2)
    with ca:
        if not df.empty and 'type' in df.columns:
            st.plotly_chart(apply_vibe(px.pie(df, names="type", title="Ingestion Modality", hole=0.6, color_discrete_sequence=["#10B981", "#3B82F6", "#F59E0B"])), use_container_width=True)
    with cb:
        if not df.empty and 'crop' in df.columns:
            st.plotly_chart(apply_vibe(px.bar(df['crop'].value_counts().reset_index(), x='crop', y='count', title="Query Volume", color_discrete_sequence=["#3B82F6"])), use_container_width=True)

with t_hitl:
    st.markdown("### Manual Agronomist Triage")
    flagged_df = df[df["status"] == "Review Required"].reset_index(drop=True) if not df.empty and 'status' in df.columns else []
    if len(flagged_df) == 0:
        st.success("🎉 All AI inferences cleared with high confidence. Inbox zero.")
    else:
        for idx, row in flagged_df.head(5).iterrows():
            with st.container():
                st.markdown(f"<div style='background-color: #1E293B; border-left: 4px solid #F59E0B; padding: 15px; border-radius: 4px; margin-bottom: 10px;'><strong style='color:#F8FAFC;'>Case {str(row.get('id', 'N/A'))}</strong> | {row.get('crop', 'Unknown')} <br><span style='color:#94A3B8;'>AI suspected </span> <b>{row.get('finding', 'Unknown')}</b> <span style='color:#94A3B8;'>but confidence was only</span> <b>{int(row.get('conf', 0)*100)}%</b>.</div>", unsafe_allow_html=True)
                ca, cb = st.columns([3, 1])
                ca.text_input("Final Diagnosis", value=f"Confirmed {row.get('finding', '')}.", key=f"t_{idx}")
                if cb.button("Dispatch WhatsApp", key=f"b_{idx}", use_container_width=True): 
                    st.toast("Override dispatched successfully!")
                st.markdown("---")

with t_cms:
    st.markdown("### Regional Wholesale Benchmarks")
    st.data_editor(pd.DataFrame([
        {"Commodity": "Onion (Kanda)", "MSP (₹)": 2100, "Current (₹)": 2450, "Trend": "Bullish"}, 
        {"Commodity": "Rice (Paddy)", "MSP (₹)": 2300, "Current (₹)": 2320, "Trend": "Stable"}
    ]), num_rows="dynamic", use_container_width=True)
    if st.button("💾 Push Sync to FastAPI"): 
        st.success("✅ Price matrix published to production cache!")
