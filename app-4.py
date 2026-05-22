import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import warnings
warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────
#  PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Nassau Candy – Shipping Analytics",
    page_icon="🍬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
#  THEME / CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
    /* Main palette */
    :root {
        --primary: #7C3AED;
        --accent:  #F59E0B;
        --good:    #10B981;
        --bad:     #EF4444;
        --bg-card: #1E1E2E;
    }

    /* Hide Streamlit chrome */
    #MainMenu {visibility: hidden;}
    footer    {visibility: hidden;}
    header    {visibility: hidden;}

    /* Section header */
    .section-header {
        font-size: 1.05rem;
        font-weight: 700;
        color: #A78BFA;
        text-transform: uppercase;
        letter-spacing: .08em;
        margin: 1.4rem 0 .5rem;
    }

    /* KPI card */
    .kpi-card {
        background: linear-gradient(135deg, #1E1E2E 0%, #2A2A3E 100%);
        border: 1px solid #3F3F5F;
        border-radius: 12px;
        padding: 18px 22px;
        text-align: center;
    }
    .kpi-label  { font-size: .75rem; color: #9CA3AF; text-transform: uppercase; letter-spacing: .06em; }
    .kpi-value  { font-size: 2rem;   font-weight: 800; color: #F3F4F6; line-height: 1.1; }
    .kpi-delta  { font-size: .78rem; color: #6EE7B7; margin-top: 2px; }
    .kpi-delta.bad { color: #FCA5A5; }

    /* Route badge */
    .badge-eff   { background:#064E3B; color:#6EE7B7; padding:2px 8px; border-radius:999px; font-size:.7rem; font-weight:700; }
    .badge-ineff { background:#7F1D1D; color:#FCA5A5; padding:2px 8px; border-radius:999px; font-size:.7rem; font-weight:700; }

    /* Divider */
    .hdivider { border:none; border-top:1px solid #3F3F5F; margin: 1rem 0; }

    /* Data note box */
    .data-note {
        background:#1C1C2E; border-left:3px solid #F59E0B;
        padding:10px 14px; border-radius:0 8px 8px 0;
        font-size:.82rem; color:#D1D5DB; margin-bottom:1rem;
    }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  STATIC LOOKUP TABLES
# ─────────────────────────────────────────────
PRODUCT_FACTORY = {
    "Wonka Bar - Nutty Crunch Surprise":   "Lot's O' Nuts",
    "Wonka Bar - Fudge Mallows":           "Lot's O' Nuts",
    "Wonka Bar -Scrumdiddlyumptious":      "Lot's O' Nuts",
    "Wonka Bar - Milk Chocolate":          "Wicked Choccy's",
    "Wonka Bar - Triple Dazzle Caramel":   "Wicked Choccy's",
    "Laffy Taffy":                         "Sugar Shack",
    "SweeTARTS":                           "Sugar Shack",
    "Nerds":                               "Sugar Shack",
    "Fun Dip":                             "Sugar Shack",
    "Fizzy Lifting Drinks":                "Sugar Shack",
    "Everlasting Gobstopper":              "Secret Factory",
    "Hair Toffee":                         "The Other Factory",
    "Lickable Wallpaper":                  "Secret Factory",
    "Wonka Gum":                           "Secret Factory",
    "Kazookles":                           "The Other Factory",
}

FACTORY_COORDS = {
    "Lot's O' Nuts":       {"lat": 32.881893, "lon": -111.768036, "state": "Arizona"},
    "Wicked Choccy's":     {"lat": 32.076176, "lon": -81.088371,  "state": "Georgia"},
    "Sugar Shack":         {"lat": 48.11914,  "lon": -96.18115,   "state": "Minnesota"},
    "Secret Factory":      {"lat": 41.446333, "lon": -90.565487,  "state": "Illinois"},
    "The Other Factory":   {"lat": 35.1175,   "lon": -89.971107,  "state": "Tennessee"},
}

FACTORY_COLORS = {
    "Lot's O' Nuts":       "#7C3AED",
    "Wicked Choccy's":     "#F59E0B",
    "Sugar Shack":         "#10B981",
    "Secret Factory":      "#3B82F6",
    "The Other Factory":   "#EF4444",
}

STATE_ABBREV = {
    "Alabama":"AL","Alaska":"AK","Arizona":"AZ","Arkansas":"AR","California":"CA",
    "Colorado":"CO","Connecticut":"CT","Delaware":"DE","District of Columbia":"DC",
    "Florida":"FL","Georgia":"GA","Hawaii":"HI","Idaho":"ID","Illinois":"IL",
    "Indiana":"IN","Iowa":"IA","Kansas":"KS","Kentucky":"KY","Louisiana":"LA",
    "Maine":"ME","Maryland":"MD","Massachusetts":"MA","Michigan":"MI","Minnesota":"MN",
    "Mississippi":"MS","Missouri":"MO","Montana":"MT","Nebraska":"NE","Nevada":"NV",
    "New Hampshire":"NH","New Jersey":"NJ","New Mexico":"NM","New York":"NY",
    "North Carolina":"NC","North Dakota":"ND","Ohio":"OH","Oklahoma":"OK","Oregon":"OR",
    "Pennsylvania":"PA","Rhode Island":"RI","South Carolina":"SC","South Dakota":"SD",
    "Tennessee":"TN","Texas":"TX","Utah":"UT","Vermont":"VT","Virginia":"VA",
    "Washington":"WA","West Virginia":"WV","Wisconsin":"WI","Wyoming":"WY",
    # Canadian provinces (kept in data, excluded from US choropleth)
    "Alberta":"AB","British Columbia":"BC","Manitoba":"MB","New Brunswick":"NB",
    "Newfoundland and Labrador":"NL","Nova Scotia":"NS","Ontario":"ON",
    "Prince Edward Island":"PE","Quebec":"QC","Saskatchewan":"SK",
}

SHIP_MODE_ORDER = ["Same Day", "First Class", "Second Class", "Standard Class"]
SHIP_MODE_COLORS = {
    "Same Day":       "#7C3AED",
    "First Class":    "#3B82F6",
    "Second Class":   "#10B981",
    "Standard Class": "#F59E0B",
}


# ─────────────────────────────────────────────
#  DATA LOADING & PROCESSING
# ─────────────────────────────────────────────
@st.cache_data(show_spinner="Loading and processing data…")
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)

    # Parse dates (DD-MM-YYYY format in this dataset)
    df["Order Date"] = pd.to_datetime(df["Order Date"], dayfirst=True, errors="coerce")
    df["Ship Date"]  = pd.to_datetime(df["Ship Date"],  dayfirst=True, errors="coerce")

    # Drop rows with missing dates
    df = df.dropna(subset=["Order Date", "Ship Date"])

    # Lead time in days (raw)
    df["Lead Time"] = (df["Ship Date"] - df["Order Date"]).dt.days

    # Remove invalid lead times
    df = df[df["Lead Time"] > 0].copy()

    # Factory enrichment
    df["Factory"] = df["Product Name"].map(PRODUCT_FACTORY)
    df["Factory Lat"] = df["Factory"].map(lambda f: FACTORY_COORDS.get(f, {}).get("lat"))
    df["Factory Lon"] = df["Factory"].map(lambda f: FACTORY_COORDS.get(f, {}).get("lon"))

    # Route definitions
    df["Route"]        = df["Factory"] + " → " + df["State/Province"]
    df["Route_Region"] = df["Factory"] + " → " + df["Region"]

    # State abbreviation
    df["State_Abbrev"] = df["State/Province"].map(STATE_ABBREV)

    # Helper columns
    df["Order Month"] = df["Order Date"].dt.to_period("M").astype(str)
    df["Order Year"]  = df["Order Date"].dt.year
    df["Is_US"]       = df["State/Province"].isin([s for s,a in STATE_ABBREV.items() if len(a)==2 and a not in ("AB","BC","MB","NB","NL","NS","ON","PE","QC","SK")])

    return df


@st.cache_data(show_spinner=False)
def load_us_geojson():
    """Fetch US states GeoJSON — cached so it only downloads once."""
    urls = [
        "https://raw.githubusercontent.com/PublicaMundi/MappingAPI/master/data/geojson/us-states.json",
        "https://raw.githubusercontent.com/python-visualization/folium/master/examples/data/us-states.json",
    ]
    for url in urls:
        try:
            r = requests.get(url, timeout=20)
            if r.status_code == 200:
                return r.json()
        except Exception:
            continue
    return None


@st.cache_data(show_spinner=False)
def build_route_table(df: pd.DataFrame, delay_threshold: int) -> pd.DataFrame:
    df2 = df.copy()
    df2["Delayed"] = (df2["Lead Time"] > delay_threshold).astype(int)

    agg = df2.groupby("Route").agg(
        Factory          = ("Factory",    "first"),
        State            = ("State/Province", "first"),
        Region           = ("Region",     "first"),
        Total_Shipments  = ("Lead Time",  "count"),
        Avg_Lead_Time    = ("Lead Time",  "mean"),
        Median_Lead_Time = ("Lead Time",  "median"),
        Std_Lead_Time    = ("Lead Time",  "std"),
        Min_Lead_Time    = ("Lead Time",  "min"),
        Max_Lead_Time    = ("Lead Time",  "max"),
        Delayed_Count    = ("Delayed",    "sum"),
        Total_Sales      = ("Sales",      "sum"),
        Total_Profit     = ("Gross Profit","sum"),
    ).reset_index()

    agg["Std_Lead_Time"]   = agg["Std_Lead_Time"].fillna(0).round(1)
    agg["Delay_Rate_Pct"]  = (agg["Delayed_Count"] / agg["Total_Shipments"] * 100).round(1)
    agg["Avg_Lead_Time"]   = agg["Avg_Lead_Time"].round(1)

    # Filter minimum volume
    agg = agg[agg["Total_Shipments"] >= 3].copy()

    # Efficiency score (0 = worst, 100 = best)
    mn, mx = agg["Avg_Lead_Time"].min(), agg["Avg_Lead_Time"].max()
    if mx > mn:
        agg["Efficiency_Score"] = ((mx - agg["Avg_Lead_Time"]) / (mx - mn) * 100).round(1)
    else:
        agg["Efficiency_Score"] = 100.0

    agg = agg.sort_values("Efficiency_Score", ascending=False).reset_index(drop=True)
    agg["Rank"] = agg.index + 1
    return agg


# ─────────────────────────────────────────────
#  LOAD DATA
# ─────────────────────────────────────────────
DATA_PATH = "Nassau_Candy_Distributor.csv"
df_raw = load_data(DATA_PATH)


# ─────────────────────────────────────────────
#  SIDEBAR FILTERS
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🍬 Nassau Candy")
    st.markdown("**Shipping Route Analytics**")
    st.markdown('<hr class="hdivider">', unsafe_allow_html=True)

    # Date range
    st.markdown('<p class="section-header">📅 Date Range</p>', unsafe_allow_html=True)
    min_date = df_raw["Order Date"].min().date()
    max_date = df_raw["Order Date"].max().date()
    _date_result = st.date_input(
        "Order date range",
        value=(min_date, max_date),
        min_value=min_date, max_value=max_date,
        label_visibility="collapsed",
    )
    if isinstance(_date_result, (list, tuple)) and len(_date_result) == 2:
        date_from, date_to = _date_result
    else:
        # Mid-selection: only start date chosen yet — wait silently
        st.stop()

    # Region
    st.markdown('<p class="section-header">🌎 Region</p>', unsafe_allow_html=True)
    all_regions = sorted(df_raw["Region"].unique())
    sel_regions = st.multiselect("Regions", all_regions, default=all_regions, label_visibility="collapsed")

    # State — filtered to only states within selected regions
    st.markdown('<p class="section-header">📍 State / Province</p>', unsafe_allow_html=True)
    if sel_regions:
        state_pool = sorted(df_raw[df_raw["Region"].isin(sel_regions)]["State/Province"].unique())
    else:
        state_pool = sorted(df_raw["State/Province"].unique())
    sel_states = st.multiselect("States", state_pool, default=state_pool, label_visibility="collapsed")
    if not sel_states:
        sel_states = state_pool   # fallback: if user clears all, show all

    # Ship Mode
    st.markdown('<p class="section-header">🚚 Ship Mode</p>', unsafe_allow_html=True)
    all_modes = SHIP_MODE_ORDER
    sel_modes = st.multiselect("Ship Modes", all_modes, default=all_modes, label_visibility="collapsed")

    # Factory
    st.markdown('<p class="section-header">🏭 Factory</p>', unsafe_allow_html=True)
    all_factories = sorted(df_raw["Factory"].dropna().unique())
    sel_factories = st.multiselect("Factories", all_factories, default=all_factories, label_visibility="collapsed")

    # Delay threshold
    st.markdown('<p class="section-header">⏱ Delay Threshold (days)</p>', unsafe_allow_html=True)
    lt_min = int(df_raw["Lead Time"].min())
    lt_max = int(df_raw["Lead Time"].max())
    lt_median = int(df_raw["Lead Time"].median())
    delay_thresh = st.slider(
        "Lead time above which a shipment is 'delayed'",
        min_value=lt_min, max_value=lt_max,
        value=lt_median, step=1,
        label_visibility="collapsed",
    )
    st.caption(f"Median lead time: **{lt_median} days** | Threshold: **{delay_thresh} days**")

    st.markdown('<hr class="hdivider">', unsafe_allow_html=True)
    st.caption("📊 Nassau Candy Distributor\nFactory-to-Customer Route Efficiency Dashboard")


# ─────────────────────────────────────────────
#  APPLY FILTERS
# ─────────────────────────────────────────────
df = df_raw.copy()
df = df[(df["Order Date"].dt.date >= date_from) & (df["Order Date"].dt.date <= date_to)]
if sel_regions:
    df = df[df["Region"].isin(sel_regions)]
if sel_states:
    df = df[df["State/Province"].isin(sel_states)]
if sel_modes:
    df = df[df["Ship Mode"].isin(sel_modes)]
if sel_factories:
    df = df[df["Factory"].isin(sel_factories)]

df["Delayed"] = (df["Lead Time"] > delay_thresh).astype(int)
route_df = build_route_table(df, delay_thresh)
us_df = df[df["Is_US"]].copy()


# ─────────────────────────────────────────────
#  HEADER
# ─────────────────────────────────────────────
st.markdown("# 🍬 Nassau Candy Distributor")
st.markdown("### Factory-to-Customer Shipping Route Efficiency Dashboard")

st.markdown(f"""
<div class="data-note">
  ⚠️ <strong>Data Note:</strong> Ship dates in this dataset extend several years beyond order dates
  (order dates: {df_raw['Order Date'].min().strftime('%b %Y')} – {df_raw['Order Date'].max().strftime('%b %Y')};
  ship dates: {df_raw['Ship Date'].min().strftime('%b %Y')} – {df_raw['Ship Date'].max().strftime('%b %Y')}).
  Lead times are therefore large in absolute terms (900–1,640 days) but all relative comparisons,
  rankings, and efficiency scores remain fully valid. Analysis focuses on <em>relative performance</em> across routes.
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  TOP KPI ROW
# ─────────────────────────────────────────────
total_orders   = len(df)
total_routes   = len(route_df)
avg_lt         = df["Lead Time"].mean()
delay_rate     = df["Delayed"].mean() * 100
total_sales    = df["Sales"].sum()
total_profit   = df["Gross Profit"].sum()

c1, c2, c3, c4, c5, c6 = st.columns(6)
kpi_data = [
    (c1, "Total Orders",     f"{total_orders:,}",        "across all routes"),
    (c2, "Active Routes",    f"{total_routes}",           "factory → state pairs"),
    (c3, "Avg Lead Time",    f"{avg_lt:.0f} days",        "mean across filtered orders"),
    (c4, "Delay Rate",       f"{delay_rate:.1f}%",        f"threshold: {delay_thresh} days", delay_rate > 50),
    (c5, "Total Sales",      f"${total_sales:,.0f}",      "filtered period"),
    (c6, "Total Profit",     f"${total_profit:,.0f}",     "gross profit"),
]
for col, label, value, delta, *bad in kpi_data:
    is_bad = bad[0] if bad else False
    delta_cls = "bad" if is_bad else ""
    with col:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
            <div class="kpi-delta {delta_cls}">{delta}</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  TABS
# ─────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "📋  Route Efficiency Overview",
    "🗺️  Geographic Shipping Map",
    "🚚  Ship Mode Comparison",
    "🔍  Route Drill-Down",
])


# ═══════════════════════════════════════════════
#  TAB 1 – ROUTE EFFICIENCY OVERVIEW
# ═══════════════════════════════════════════════
with tab1:
    st.markdown("## Route Efficiency Overview")
    st.markdown("Ranking of all factory-to-customer-state routes by average shipping lead time.")

    # ── Leaderboard table — full width ─────────
    st.markdown('<p class="section-header">📊 Route Performance Leaderboard</p>', unsafe_allow_html=True)

    display_df = route_df[["Rank","Route","Factory","State","Region",
                            "Total_Shipments","Avg_Lead_Time","Std_Lead_Time",
                            "Delay_Rate_Pct","Efficiency_Score"]].copy()
    display_df.columns = ["#","Route","Factory","State","Region",
                           "Shipments","Avg Lead Time","Std Dev",
                           "Delay %","Efficiency Score"]

    def color_efficiency(val):
        if val >= 70: return "background-color:#064E3B; color:#6EE7B7"
        if val >= 40: return "background-color:#1E3A5F; color:#93C5FD"
        return "background-color:#7F1D1D; color:#FCA5A5"

    def color_delay(val):
        if val <= 20: return "color:#6EE7B7"
        if val <= 50: return "color:#FCD34D"
        return "color:#FCA5A5"

    styled = (display_df.style
              .map(color_efficiency, subset=["Efficiency Score"])
              .map(color_delay,      subset=["Delay %"])
              .format({"Avg Lead Time":"{:.1f}","Std Dev":"{:.1f}",
                        "Delay %":"{:.1f}%","Efficiency Score":"{:.1f}"}))
    st.dataframe(styled, height=700, use_container_width=True, hide_index=True)

    st.markdown('<hr class="hdivider">', unsafe_allow_html=True)

    # ── Top / Bottom 10 — side by side, full height, no toolbar ──
    col_l, col_r = st.columns(2, gap="large")

    with col_l:
        st.markdown('<p class="section-header">🏆 Top 10 Most Efficient Routes</p>', unsafe_allow_html=True)
        top10 = route_df.nlargest(10, "Efficiency_Score").sort_values("Efficiency_Score")
        fig_top = px.bar(
            top10,
            x="Efficiency_Score", y="Route",
            orientation="h",
            color="Efficiency_Score",
            color_continuous_scale=[[0,"#064E3B"],[1,"#6EE7B7"]],
            text="Efficiency_Score",
            labels={"Efficiency_Score":"Efficiency Score","Route":""},
        )
        fig_top.update_traces(texttemplate="%{text:.1f}", textposition="outside")
        fig_top.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_color="#D1D5DB", showlegend=False,
            coloraxis_showscale=False,
            margin=dict(l=10, r=80, t=10, b=10),
            height=420,
            xaxis=dict(range=[0, top10["Efficiency_Score"].max() * 1.18],
                       showgrid=False, visible=False),
            yaxis=dict(tickfont=dict(size=11)),
        )
        st.plotly_chart(fig_top, use_container_width=True,
                        config={"displayModeBar": False})

    with col_r:
        st.markdown('<p class="section-header">⚠️ Bottom 10 Least Efficient Routes</p>', unsafe_allow_html=True)
        bot10 = route_df.nsmallest(10, "Efficiency_Score").sort_values("Avg_Lead_Time", ascending=False)
        fig_bot = px.bar(
            bot10,
            x="Avg_Lead_Time", y="Route",
            orientation="h",
            color="Avg_Lead_Time",
            color_continuous_scale=[[0,"#7F1D1D"],[1,"#FCA5A5"]],
            text="Avg_Lead_Time",
            labels={"Avg_Lead_Time":"Avg Lead Time (days)","Route":""},
        )
        fig_bot.update_traces(texttemplate="%{text:.0f}d", textposition="outside")
        fig_bot.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_color="#D1D5DB", showlegend=False,
            coloraxis_showscale=False,
            margin=dict(l=10, r=80, t=10, b=10),
            height=420,
            xaxis=dict(range=[0, bot10["Avg_Lead_Time"].max() * 1.15],
                       showgrid=False, visible=False),
            yaxis=dict(tickfont=dict(size=11)),
        )
        st.plotly_chart(fig_bot, use_container_width=True,
                        config={"displayModeBar": False})

    st.markdown('<hr class="hdivider">', unsafe_allow_html=True)

    # ── Factory comparison ────────────────────
    st.markdown('<p class="section-header">🏭 Factory Performance Comparison</p>', unsafe_allow_html=True)
    c1, c2 = st.columns(2, gap="large")

    with c1:
        fac_agg = df.groupby("Factory").agg(
            Avg_LT      = ("Lead Time","mean"),
            Orders      = ("Lead Time","count"),
            Delay_Rate  = ("Delayed","mean"),
        ).reset_index()
        fac_agg["Delay_Rate"] *= 100
        fac_agg["color"] = fac_agg["Factory"].map(FACTORY_COLORS)

        fig_fac = px.scatter(
            fac_agg,
            x="Avg_LT", y="Delay_Rate",
            size="Orders", color="Factory",
            color_discrete_map=FACTORY_COLORS,
            text="Factory",
            size_max=55,
            labels={"Avg_LT":"Avg Lead Time (days)","Delay_Rate":"Delay Rate (%)"},
            title="Factory Bubble Chart: Lead Time vs Delay Rate (size = volume)",
        )
        fig_fac.update_traces(textposition="top center", textfont_size=10)
        fig_fac.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_color="#D1D5DB", showlegend=False,
            margin=dict(l=0,r=0,t=40,b=0), height=380,
        )
        fig_fac.update_xaxes(gridcolor="#2A2A3E")
        fig_fac.update_yaxes(gridcolor="#2A2A3E")
        st.plotly_chart(fig_fac, use_container_width=True,
                        config={"displayModeBar": False})

    with c2:
        fac_region = df.groupby(["Factory","Region"])["Lead Time"].mean().reset_index()
        fac_region.columns = ["Factory","Region","Avg_LT"]
        fig_heat = px.density_heatmap(
            fac_region,
            x="Region", y="Factory",
            z="Avg_LT",
            color_continuous_scale="RdYlGn_r",
            title="Avg Lead Time Heatmap: Factory × Region",
            labels={"Avg_LT":"Avg Lead Time"},
            text_auto=".0f",
        )
        fig_heat.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_color="#D1D5DB", margin=dict(l=0,r=0,t=40,b=0), height=380,
        )
        st.plotly_chart(fig_heat, use_container_width=True,
                        config={"displayModeBar": False})


# ═══════════════════════════════════════════════
#  TAB 2 – GEOGRAPHIC MAP
# ═══════════════════════════════════════════════
with tab2:
    st.markdown("## Geographic Shipping Map")
    st.markdown("US state-level heatmap of shipping efficiency, with factory locations overlaid.")

    map_metric = st.radio(
        "Color states by:",
        ["Avg Lead Time", "Delay Rate %", "Shipment Volume"],
        horizontal=True,
    )

    # Aggregate by state (US only)
    state_agg = us_df.groupby(["State/Province","State_Abbrev"]).agg(
        Avg_Lead_Time  = ("Lead Time","mean"),
        Delay_Rate     = ("Delayed","mean"),
        Shipments      = ("Lead Time","count"),
        Avg_Sales      = ("Sales","mean"),
    ).reset_index()
    state_agg["Delay_Rate"] = (state_agg["Delay_Rate"] * 100).round(1)
    state_agg["Avg_Lead_Time"] = state_agg["Avg_Lead_Time"].round(1)

    metric_map = {
        "Avg Lead Time":    ("Avg_Lead_Time",  "RdYlGn_r", "Avg Lead Time (days)"),
        "Delay Rate %":     ("Delay_Rate",     "RdYlGn_r", "Delay Rate (%)"),
        "Shipment Volume":  ("Shipments",      "Blues",     "Shipment Count"),
    }
    z_col, color_scale, color_label = metric_map[map_metric]

    # Build hover text
    state_agg["hover_text"] = (
        "<b>" + state_agg["State/Province"] + "</b><br>" +
        "Avg Lead Time: " + state_agg["Avg_Lead_Time"].round(1).astype(str) + " days<br>" +
        "Delay Rate: "    + state_agg["Delay_Rate"].round(1).astype(str) + "%<br>" +
        "Orders: "        + state_agg["Shipments"].astype(str)
    )

    geojson = load_us_geojson()

    if geojson is None:
        st.error("⚠️ Could not load map boundary data. Check internet connection.")
    else:
        fig_map = px.choropleth_map(
            state_agg,
            geojson=geojson,
            locations="State/Province",
            featureidkey="properties.name",
            color=z_col,
            color_continuous_scale=color_scale,
            center={"lat": 38.0, "lon": -96.0},
            zoom=2.9,
            map_style="carto-darkmatter",
            hover_name="State/Province",
            hover_data={
                "Avg_Lead_Time": ":.1f",
                "Delay_Rate":    ":.1f",
                "Shipments":     True,
                "State/Province": False,
            },
            labels={"Avg_Lead_Time": "Avg Lead Time", "Delay_Rate": "Delay %", "Shipments": "Orders"},
            title=f"US State-Level Shipping Performance — {map_metric}",
            opacity=0.75,
        )

        # Factory markers
        for factory, coords in FACTORY_COORDS.items():
            if factory in sel_factories:
                fig_map.add_trace(go.Scattermap(
                    lat=[coords["lat"]],
                    lon=[coords["lon"]],
                    mode="markers+text",
                    marker=dict(size=14, color=FACTORY_COLORS[factory]),
                    text=[factory],
                    textposition="top right",
                    textfont=dict(size=10, color="white"),
                    name=factory,
                    showlegend=True,
                ))

        fig_map.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="#D1D5DB",
            title=dict(font=dict(color="#D1D5DB", size=14)),
            legend=dict(
                bgcolor="rgba(30,30,46,0.9)", bordercolor="#3F3F5F",
                borderwidth=1, font_size=11, title_text="Factories",
                x=0.01, y=0.01, xanchor="left", yanchor="bottom",
            ),
            margin=dict(l=0, r=0, t=40, b=0),
            height=520,
            coloraxis_colorbar=dict(
                title=color_label,
                tickfont=dict(color="#D1D5DB"),
                title_font=dict(color="#D1D5DB"),
            ),
        )

        st.plotly_chart(fig_map, use_container_width=True,
                        config={"displayModeBar": False})
        st.caption("💡 Click and drag on the map to pan · Scroll to zoom in/out")

    # ── State bottleneck table ─────────────────
    st.markdown('<hr class="hdivider">', unsafe_allow_html=True)
    st.markdown('<p class="section-header">🔥 Geographic Bottleneck Analysis</p>', unsafe_allow_html=True)

    c1, c2 = st.columns(2, gap="large")

    with c1:
        st.markdown("**States with Highest Avg Lead Time**")
        top_lt_states = state_agg.nlargest(10,"Avg_Lead_Time")[
            ["State/Province","Avg_Lead_Time","Shipments","Delay_Rate"]
        ].rename(columns={"State/Province":"State","Avg_Lead_Time":"Avg Lead Time",
                           "Delay_Rate":"Delay %"})
        st.dataframe(top_lt_states.set_index("State"), use_container_width=True)

    with c2:
        st.markdown("**High-Volume Bottleneck States** (volume × delay)")
        state_agg["Bottleneck_Score"] = (
            state_agg["Shipments"] * state_agg["Delay_Rate"] / 100
        ).round(1)
        bottleneck = state_agg.nlargest(10,"Bottleneck_Score")[
            ["State/Province","Shipments","Delay_Rate","Bottleneck_Score"]
        ].rename(columns={"State/Province":"State","Delay_Rate":"Delay %",
                           "Bottleneck_Score":"Bottleneck Score"})
        st.dataframe(bottleneck.set_index("State"), use_container_width=True)

    # ── Regional summary bars ──────────────────
    st.markdown('<p class="section-header">📍 Regional Summary</p>', unsafe_allow_html=True)
    reg_agg = df.groupby("Region").agg(
        Avg_Lead_Time = ("Lead Time","mean"),
        Delay_Rate    = ("Delayed","mean"),
        Shipments     = ("Lead Time","count"),
    ).reset_index()
    reg_agg["Delay_Rate"] = (reg_agg["Delay_Rate"] * 100).round(1)

    fig_reg = make_subplots(rows=1, cols=2,
                            subplot_titles=("Avg Lead Time by Region",
                                            "Delay Rate % by Region"))
    fig_reg.add_trace(go.Bar(
        x=reg_agg["Region"], y=reg_agg["Avg_Lead_Time"],
        marker_color=["#7C3AED","#F59E0B","#10B981","#3B82F6"],
        text=reg_agg["Avg_Lead_Time"].round(0),
        texttemplate="%{text:.0f}d", textposition="outside",
        name="Avg Lead Time",
    ), row=1, col=1)
    fig_reg.add_trace(go.Bar(
        x=reg_agg["Region"], y=reg_agg["Delay_Rate"],
        marker_color=["#EF4444","#F59E0B","#10B981","#3B82F6"],
        text=reg_agg["Delay_Rate"],
        texttemplate="%{text:.1f}%", textposition="outside",
        name="Delay Rate",
    ), row=1, col=2)
    fig_reg.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font_color="#D1D5DB", showlegend=False,
        margin=dict(l=0,r=0,t=40,b=0), height=320,
    )
    for i in [1,2]:
        fig_reg.update_xaxes(gridcolor="#2A2A3E", row=1, col=i)
        fig_reg.update_yaxes(gridcolor="#2A2A3E", row=1, col=i)
    st.plotly_chart(fig_reg, use_container_width=True,
                    config={"displayModeBar": False})


# ═══════════════════════════════════════════════
#  TAB 3 – SHIP MODE COMPARISON
# ═══════════════════════════════════════════════
with tab3:
    st.markdown("## Ship Mode Performance Analysis")
    st.markdown("Comparing efficiency across Standard Class, Second Class, First Class, and Same Day shipping.")

    # ── KPI cards by mode ─────────────────────
    mode_agg = df.groupby("Ship Mode").agg(
        Orders       = ("Lead Time","count"),
        Avg_LT       = ("Lead Time","mean"),
        Median_LT    = ("Lead Time","median"),
        Std_LT       = ("Lead Time","std"),
        Delay_Rate   = ("Delayed","mean"),
        Avg_Sales    = ("Sales","mean"),
        Total_Sales  = ("Sales","sum"),
    ).reset_index()
    mode_agg["Delay_Rate"] = (mode_agg["Delay_Rate"]*100).round(1)
    _available_modes = mode_agg["Ship Mode"].tolist()
    mode_agg = (mode_agg.set_index("Ship Mode")
                .reindex([m for m in SHIP_MODE_ORDER if m in _available_modes])
                .reset_index())

    if len(mode_agg) == 0:
        st.warning("No data available for the selected ship modes. Adjust your sidebar filters.")
    else:
        cols = st.columns(len(mode_agg))
        for i, row in mode_agg.iterrows():
            color = SHIP_MODE_COLORS.get(row["Ship Mode"],"#6B7280")
            with cols[i]:
                st.markdown(f"""
                <div class="kpi-card" style="border-color:{color}40;">
                    <div class="kpi-label" style="color:{color};">{row['Ship Mode']}</div>
                    <div class="kpi-value">{row['Avg_LT']:.0f}d</div>
                    <div class="kpi-delta">{row['Orders']:,} orders · {row['Delay_Rate']:.1f}% delayed</div>
                </div>
                """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Distribution charts ───────────────────
    c1, c2 = st.columns(2, gap="large")

    with c1:
        st.markdown('<p class="section-header">📦 Lead Time Distribution by Ship Mode</p>', unsafe_allow_html=True)
        fig_box = go.Figure()
        for mode in SHIP_MODE_ORDER:
            sub = df[df["Ship Mode"] == mode]["Lead Time"]
            if len(sub) == 0:
                continue
            fig_box.add_trace(go.Box(
                y=sub, name=mode,
                marker_color=SHIP_MODE_COLORS.get(mode,"#6B7280"),
                boxmean="sd",
                line_width=1.5,
            ))
        fig_box.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_color="#D1D5DB",
            yaxis_title="Lead Time (days)",
            hovermode="closest",
            margin=dict(l=0,r=0,t=20,b=0), height=380,
        )
        fig_box.update_yaxes(gridcolor="#2A2A3E")
        st.plotly_chart(fig_box, use_container_width=True,
                        config={"displayModeBar": False})
        st.caption("💡 Double-click to reset zoom")

    with c2:
        st.markdown('<p class="section-header">📈 Avg Lead Time by Mode × Region</p>', unsafe_allow_html=True)
        mr_agg = df.groupby(["Ship Mode","Region"])["Lead Time"].mean().reset_index()
        fig_mr = px.bar(
            mr_agg, x="Region", y="Lead Time",
            color="Ship Mode",
            color_discrete_map=SHIP_MODE_COLORS,
            barmode="group",
            labels={"Lead Time":"Avg Lead Time (days)"},
        )
        fig_mr.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_color="#D1D5DB",
            margin=dict(l=0,r=0,t=20,b=0), height=380,
            legend=dict(bgcolor="rgba(0,0,0,0)"),
        )
        fig_mr.update_yaxes(gridcolor="#2A2A3E")
        fig_mr.update_xaxes(gridcolor="#2A2A3E")
        st.plotly_chart(fig_mr, use_container_width=True,
                        config={"displayModeBar": False})

    st.markdown('<hr class="hdivider">', unsafe_allow_html=True)

    # ── Delay rate + cost tradeoff ─────────────
    c1, c2 = st.columns(2, gap="large")

    with c1:
        st.markdown('<p class="section-header">⚠️ Delay Rate by Ship Mode</p>', unsafe_allow_html=True)
        fig_delay = px.bar(
            mode_agg, x="Ship Mode", y="Delay_Rate",
            color="Ship Mode",
            color_discrete_map=SHIP_MODE_COLORS,
            text="Delay_Rate",
            labels={"Delay_Rate":"Delay Rate (%)","Ship Mode":""},
        )
        fig_delay.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        fig_delay.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_color="#D1D5DB", showlegend=False,
            margin=dict(l=0,r=0,t=20,b=0), height=340,
        )
        fig_delay.update_yaxes(gridcolor="#2A2A3E")
        st.plotly_chart(fig_delay, use_container_width=True,
                        config={"displayModeBar": False})

    with c2:
        st.markdown('<p class="section-header">💰 Cost-Time Tradeoff (Avg Sales per Order)</p>', unsafe_allow_html=True)
        fig_ct = px.scatter(
            mode_agg,
            x="Avg_LT", y="Avg_Sales",
            color="Ship Mode",
            color_discrete_map=SHIP_MODE_COLORS,
            size="Orders",
            size_max=50,
            text="Ship Mode",
            labels={"Avg_LT":"Avg Lead Time (days)","Avg_Sales":"Avg Sales per Order ($)"},
        )
        fig_ct.update_traces(textposition="top center", textfont_size=10)
        fig_ct.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_color="#D1D5DB", showlegend=False,
            margin=dict(l=0,r=0,t=20,b=0), height=340,
        )
        fig_ct.update_xaxes(gridcolor="#2A2A3E")
        fig_ct.update_yaxes(gridcolor="#2A2A3E")
        st.plotly_chart(fig_ct, use_container_width=True,
                        config={"displayModeBar": False})

    st.markdown('<hr class="hdivider">', unsafe_allow_html=True)

    # ── Monthly trend by ship mode ─────────────
    st.markdown('<p class="section-header">📅 Monthly Avg Lead Time Trend by Ship Mode</p>', unsafe_allow_html=True)
    monthly = df.groupby(["Order Month","Ship Mode"])["Lead Time"].mean().reset_index()
    monthly.columns = ["Month","Ship Mode","Avg Lead Time"]
    monthly = monthly.sort_values("Month")

    fig_trend = px.line(
        monthly, x="Month", y="Avg Lead Time",
        color="Ship Mode",
        color_discrete_map=SHIP_MODE_COLORS,
        markers=True,
        labels={"Avg Lead Time":"Avg Lead Time (days)"},
    )
    fig_trend.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font_color="#D1D5DB",
        margin=dict(l=0,r=0,t=20,b=0), height=320,
        legend=dict(bgcolor="rgba(0,0,0,0)"),
        xaxis_tickangle=-45,
    )
    fig_trend.update_xaxes(gridcolor="#2A2A3E")
    fig_trend.update_yaxes(gridcolor="#2A2A3E")
    st.plotly_chart(fig_trend, use_container_width=True,
                    config={"displayModeBar": False})
    st.caption("💡 Click a legend item to hide/show a mode · Double-click to isolate · Double-click again to reset")


# ═══════════════════════════════════════════════
#  TAB 4 – ROUTE DRILL-DOWN
# ═══════════════════════════════════════════════
with tab4:
    st.markdown("## Route Drill-Down")
    st.markdown("Zoom into any factory, state, or individual route for granular shipment analytics.")

    # ── Selectors ──────────────────────────────
    col_a, col_b, col_c = st.columns(3)

    with col_a:
        sel_factory_dd = st.selectbox(
            "Select Factory",
            options=["All"] + sorted(df["Factory"].dropna().unique()),
        )
    with col_b:
        if sel_factory_dd == "All":
            state_options = ["All"] + sorted(df["State/Province"].unique())
        else:
            state_options = ["All"] + sorted(df[df["Factory"]==sel_factory_dd]["State/Province"].unique())
        sel_state_dd = st.selectbox("Select State / Province", options=state_options)
    with col_c:
        if sel_factory_dd != "All" and sel_state_dd != "All":
            route_key = f"{sel_factory_dd} → {sel_state_dd}"
            route_options = [route_key]
        elif sel_factory_dd != "All":
            route_options = ["All"] + sorted(df[df["Factory"]==sel_factory_dd]["Route"].unique())
        elif sel_state_dd != "All":
            route_options = ["All"] + sorted(df[df["State/Province"]==sel_state_dd]["Route"].unique())
        else:
            route_options = ["All"] + sorted(df["Route"].unique())
        sel_route_dd = st.selectbox("Select Specific Route", options=route_options)

    # ── Filter drill-down data ──────────────────
    dd_df = df.copy()
    if sel_factory_dd != "All":
        dd_df = dd_df[dd_df["Factory"] == sel_factory_dd]
    if sel_state_dd != "All":
        dd_df = dd_df[dd_df["State/Province"] == sel_state_dd]
    if sel_route_dd != "All":
        dd_df = dd_df[dd_df["Route"] == sel_route_dd]

    if len(dd_df) == 0:
        st.warning("No data found for this combination of filters.")
    else:
        # ── Drill KPIs ─────────────────────────
        d_orders   = len(dd_df)
        d_avg_lt   = dd_df["Lead Time"].mean()
        d_min_lt   = dd_df["Lead Time"].min()
        d_max_lt   = dd_df["Lead Time"].max()
        d_delay    = dd_df["Delayed"].mean() * 100
        d_sales    = dd_df["Sales"].sum()

        dc1,dc2,dc3,dc4,dc5,dc6 = st.columns(6)
        drill_kpis = [
            (dc1,"Orders",         f"{d_orders:,}"),
            (dc2,"Avg Lead Time",  f"{d_avg_lt:.1f}d"),
            (dc3,"Min Lead Time",  f"{d_min_lt}d"),
            (dc4,"Max Lead Time",  f"{d_max_lt}d"),
            (dc5,"Delay Rate",     f"{d_delay:.1f}%"),
            (dc6,"Total Sales",    f"${d_sales:,.0f}"),
        ]
        for col, label, value in drill_kpis:
            with col:
                st.markdown(f"""
                <div class="kpi-card">
                    <div class="kpi-label">{label}</div>
                    <div class="kpi-value" style="font-size:1.4rem;">{value}</div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        col_l, col_r = st.columns([1.4, 1], gap="large")

        with col_l:
            # ── Order-level shipment timeline ───
            st.markdown('<p class="section-header">📅 Order-Level Shipment Timeline</p>', unsafe_allow_html=True)
            timeline_df = dd_df[["Order Date","Ship Date","Lead Time","Ship Mode",
                                  "Product Name","Sales","Delayed"]].copy()
            timeline_df = timeline_df.sort_values("Order Date")
            timeline_df["Status"] = timeline_df["Delayed"].map({0:"On Time",1:"Delayed"})

            fig_tl = px.scatter(
                timeline_df,
                x="Order Date", y="Lead Time",
                color="Status",
                color_discrete_map={"On Time":"#10B981","Delayed":"#EF4444"},
                symbol="Ship Mode",
                hover_data=["Product Name","Sales","Ship Mode"],
                labels={"Lead Time":"Lead Time (days)","Order Date":"Order Date"},
                size_max=8,
            )
            fig_tl.update_traces(marker_size=7)
            fig_tl.add_hline(
                y=delay_thresh, line_dash="dash",
                line_color="#F59E0B", line_width=1.5,
                annotation_text=f"Threshold: {delay_thresh}d",
                annotation_font_color="#F59E0B",
            )
            fig_tl.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font_color="#D1D5DB",
                margin=dict(l=0,r=0,t=20,b=0), height=380,
                legend=dict(bgcolor="rgba(0,0,0,0)"),
            )
            fig_tl.update_xaxes(gridcolor="#2A2A3E")
            fig_tl.update_yaxes(gridcolor="#2A2A3E")
            st.plotly_chart(fig_tl, use_container_width=True,
                            config={"displayModeBar": False})
            st.caption("💡 Double-click to reset zoom")

        with col_r:
            # ── Product mix in selection ────────
            st.markdown('<p class="section-header">🍫 Product Mix</p>', unsafe_allow_html=True)
            prod_agg = dd_df.groupby("Product Name").agg(
                Orders   = ("Lead Time","count"),
                Avg_LT   = ("Lead Time","mean"),
                Sales    = ("Sales","sum"),
            ).reset_index().sort_values("Orders", ascending=False)

            fig_prod = px.bar(
                prod_agg,
                x="Orders", y="Product Name",
                orientation="h",
                color="Avg_LT",
                color_continuous_scale="RdYlGn_r",
                text="Orders",
                labels={"Avg_LT":"Avg LT","Orders":"# Orders","Product Name":""},
            )
            fig_prod.update_traces(textposition="outside")
            fig_prod.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font_color="#D1D5DB", coloraxis_showscale=False,
                margin=dict(l=0,r=40,t=20,b=0), height=380,
            )
            fig_prod.update_xaxes(showgrid=False, visible=False)
            fig_prod.update_yaxes(tickfont_size=10)
            st.plotly_chart(fig_prod, use_container_width=True,
                            config={"displayModeBar": False})

        st.markdown('<hr class="hdivider">', unsafe_allow_html=True)

        # ── State-level performance grid ────────
        if sel_state_dd == "All":
            st.markdown('<p class="section-header">🗺️ State-Level Performance (within selection)</p>', unsafe_allow_html=True)
            state_perf = dd_df.groupby("State/Province").agg(
                Orders     = ("Lead Time","count"),
                Avg_LT     = ("Lead Time","mean"),
                Delay_Rate = ("Delayed","mean"),
                Std_LT     = ("Lead Time","std"),
            ).reset_index()
            state_perf["Delay_Rate"] = (state_perf["Delay_Rate"]*100).round(1)
            state_perf["Avg_LT"]     = state_perf["Avg_LT"].round(1)
            state_perf["Std_LT"]     = state_perf["Std_LT"].fillna(0).round(1)
            state_perf = state_perf.sort_values("Avg_LT")

            fig_states = px.bar(
                state_perf,
                x="Avg_LT", y="State/Province",
                orientation="h",
                color="Delay_Rate",
                color_continuous_scale="RdYlGn_r",
                text="Avg_LT",
                labels={"Avg_LT":"Avg Lead Time (days)","Delay_Rate":"Delay %","State/Province":""},
                title="Avg Lead Time by State (color = delay rate %)",
                hover_data={"Orders": True, "Std_LT": True,
                            "Avg_LT": ":.0f", "Delay_Rate": ":.1f"},
            )
            fig_states.update_traces(
                texttemplate="%{text:.0f}d",
                textposition="outside",
                textfont_size=10,
            )
            n_states = len(state_perf)
            bar_height = max(500, n_states * 22)
            fig_states.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font_color="#D1D5DB",
                margin=dict(l=10, r=80, t=40, b=10),
                height=bar_height,
                yaxis=dict(tickfont=dict(size=11), autorange="reversed"),
                xaxis=dict(showgrid=True, gridcolor="#2A2A3E",
                           range=[0, state_perf["Avg_LT"].max() * 1.15]),
                coloraxis_colorbar=dict(
                    title="Delay %", tickfont_color="#D1D5DB",
                    title_font_color="#D1D5DB", len=0.4,
                ),
            )
            st.plotly_chart(fig_states, use_container_width=True,
                            config={"displayModeBar": False})
            st.caption("💡 Double-click to reset zoom")

        # ── Raw orders table ───────────────────
        st.markdown('<p class="section-header">📋 Raw Orders (filtered)</p>', unsafe_allow_html=True)
        show_cols = ["Order ID","Order Date","Ship Date","Lead Time","Ship Mode",
                     "Factory","State/Province","Product Name","Sales","Gross Profit","Status"]
        disp = dd_df.assign(Status=dd_df["Delayed"].map({0:"✅ On Time",1:"⚠️ Delayed"}))
        disp = disp[show_cols].sort_values("Order Date", ascending=False)
        disp["Order Date"] = disp["Order Date"].dt.strftime("%Y-%m-%d")
        disp["Ship Date"]  = disp["Ship Date"].dt.strftime("%Y-%m-%d")
        st.dataframe(disp.reset_index(drop=True), height=360, use_container_width=True)
