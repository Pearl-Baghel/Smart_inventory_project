from __future__ import annotations

from math import ceil
from pathlib import Path
import base64

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
ASSETS_DIR = PROJECT_ROOT / "dashboard" / "assets"

FILES = {
    "Weekly totals": PROCESSED_DIR / "weekly_item_totals.csv",
    "Weekly forecast": PROCESSED_DIR / "weekly_forecast.csv",
    "Component requirements": PROCESSED_DIR / "requirements_components.csv",
    "Recommended purchases": PROCESSED_DIR / "recommended_purchases.csv",
    "Waste log": PROCESSED_DIR / "waste_log.csv",
}

IMAGE_MAP = {
    "Chickpea Meal plate": ASSETS_DIR / "chickpea.jpg",
    "Red KidneyBean Plate": ASSETS_DIR / "rajma.png",
    "Paneer Meal plate": ASSETS_DIR / "paneer.jpg",
    "Lentil soup": ASSETS_DIR / "lentils.jpg",
    "Strawberry yogurt": ASSETS_DIR / "yogurt.jpg",
    "Pani Puri 5 Balls": ASSETS_DIR / "panipuri.jpg",
    "Pani Puri 12 Balls": ASSETS_DIR / "panipuri.jpg",
    "Pepsi Lemonade": ASSETS_DIR / "lemonade.png",
}

LOGO_PATH = ASSETS_DIR / "logo.PNG"

COMPANY_NAME = "NamasteLA"
PRIMARY = "#E67E22"
SECONDARY = "#F4D03F"
PRIMARY_DARK = "#C65D0E"
DARK = "#18243B"
SOFT_BG = "#FCF8F1"
CARD_BG = "#FFFFFF"
TEXT = "#111827"
MUTED = "#6B7280"
BORDER = "#EFCB8B"
DROPDOWN_BG = "#1F2433"


def load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def round_up_qty(value: float) -> int:
    return int(ceil(max(0, float(value))))


@st.cache_data
def load_all_data() -> dict[str, pd.DataFrame]:
    return {name: load_csv(path) for name, path in FILES.items()}


def format_date_only(df: pd.DataFrame, col: str) -> pd.DataFrame:
    if col in df.columns:
        df = df.copy()
        df[col] = pd.to_datetime(df[col], errors="coerce").dt.strftime("%Y-%m-%d")
    return df


def round_display_columns(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    df = df.copy()
    for col in cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).apply(round_up_qty)
    return df


def show_missing_file_warning(dfs: dict[str, pd.DataFrame]) -> None:
    missing = [name for name, df in dfs.items() if df.empty]
    if missing:
        st.warning(
            "Some output files are missing or empty.\n\n"
            "Run these scripts in order:\n"
            "1. python src/raw_to_sales_clean.py\n"
            "2. python src/ingest_validate.py\n"
            "3. python src/weekly_forecast.py\n"
            "4. python src/planning_requirements.py\n\n"
            f"Missing or empty files: {missing}"
        )


def image_to_base64(path: Path) -> str | None:
    if not path.exists():
        return None
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def set_forecast_background(selected_item: str):
    img_path = IMAGE_MAP.get(selected_item)

    if img_path and img_path.exists():
        ext = img_path.suffix.lower().replace(".", "")
        if ext == "jpg":
            ext = "jpeg"

        img64 = image_to_base64(img_path)

        if img64:
            st.markdown(
                f"""
                <style>
                .stApp {{
                    background-image:
                        linear-gradient(rgba(252,248,241,0.80), rgba(252,248,241,0.80)),
                        url("data:image/{ext};base64,{img64}");
                    background-size: cover;
                    background-position: center;
                    background-attachment: fixed;
                }}
                </style>
                """,
                unsafe_allow_html=True
            )


def inject_styles() -> None:
    st.markdown(
        f"""
        <style>
        .stApp {{
            background: {SOFT_BG};
            color: {DARK};
        }}

        html, body, [class*="css"], p, span, div, label, h1, h2, h3, h4, h5, h6 {{
            color: {DARK} !important;
        }}

        # .block-container {{
        #     max-width: 1440px;
        #     padding-top: 1rem;
        #     padding-bottom: 2rem;
        # }}

        # .top-accent-bar {{
        #     height: 18px;
        #     width: 100%;
        #     border-radius: 999px;
        #     background: linear-gradient(90deg, {PRIMARY} 0%, {SECONDARY} 100%);
        #     margin-bottom: 14px;
        #     box-shadow: 0 8px 20px rgba(230, 126, 34, 0.18);
        # }} 

        # .header-card {{
        #     background: linear-gradient(135deg, rgba(255,255,255,0.98) 0%, rgba(255,247,235,0.98) 100%);
        #     border: 1px solid {BORDER};
        #     border-radius: 28px;
        #     padding: 18px 22px;
        #     box-shadow: 0 12px 26px rgba(0,0,0,0.06);
        #     margin-bottom: 18px;
        # }}

        .hero-logo-wrap {{
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 80px;
            height: 100%;
        }}

        .hero-logo-wrap img {{
            max-height: 90px;
            width: auto;
            display: block;
            margin: auto;
            border-radius: 16px;
            background: rgba(255,255,255,0.45);
            padding: 4px;
            box-shadow: 0 8px 20px rgba(230, 126, 34, 0.12);
        }}

        .hero-text-wrap {{
            display: flex;
            flex-direction: column;
            justify-content: center;
            # min-height: 120px;
        }}

        .hero-title {{
            font-size: clamp(28px, 3.6vw, 52px);
            font-weight: 800;
            color: {DARK} !important;
            line-height: 1.06;
            margin-bottom: 10px;
            letter-spacing: -0.02em;
        }}

        .hero-sub {{
            font-size: clamp(14px, 1.2vw, 19px);
            color: {TEXT} !important;
            line-height: 1.6;
            max-width: 980px;
        }}

        .hero-tag {{
            display: inline-block;
            width: fit-content;
            font-size: 12px;
            font-weight: 700;
            color: {PRIMARY_DARK} !important;
            background: rgba(244, 208, 63, 0.22);
            border: 1px solid rgba(230, 126, 34, 0.22);
            padding: 6px 10px;
            border-radius: 999px;
            margin-bottom: 10px;
        }}

        .kpi-card {{
            background: {CARD_BG};
            border-radius: 18px;
            padding: 18px 20px;
            border: 1px solid {BORDER};
            box-shadow: 0 6px 18px rgba(0,0,0,0.05);
            min-height: 100px;
        }}

        .kpi-label {{
            font-size: 13px;
            color: {MUTED} !important;
            margin-bottom: 10px;
            font-weight: 600;
        }}

        .kpi-value {{
            font-size: 34px;
            font-weight: 800;
            color: {DARK} !important;
            line-height: 1;
        }}

        .section-title {{
            font-size: 18px;
            font-weight: 700;
            color: {PRIMARY} !important;
            margin-top: 8px;
            margin-bottom: 4px;
        }}

        .section-sub {{
            font-size: 14px;
            color: {MUTED} !important;
            margin-bottom: 18px;
        }}

        .panel-title {{
            font-size: 22px;
            font-weight: 800;
            color: {DARK} !important;
            margin-bottom: 6px;
        }}

        .panel-sub {{
            font-size: 13px;
            color: {MUTED} !important;
            margin-bottom: 10px;
        }}

        # .food-card {{
        #     background: white;
        #     border: 1px solid {BORDER};
        #     border-radius: 16px;
        #     padding: 10px;
        #     box-shadow: 0 6px 18px rgba(0,0,0,0.05);
        #     margin-bottom: 6px;
        # }}

        .food-img-box {{
            width: 100%;
            aspect-ratio: 1 / 1;
            overflow: hidden;
            border-radius: 12px;
            background: #fff7ed;
        }}

        .food-img-box img {{
            width: 100%;
            height: 100%;
            object-fit: cover;
            display: block;
        }}

        .food-caption {{
            text-align: center;
            font-size: 14px;
            font-weight: 700;
            color: {DARK} !important;
            margin-top: 8px;
            min-height: 24px;
        }}

        .nav-btn-wrap {{
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 230px;
        }}

        div[data-testid="stMetric"] {{
            background: white;
            border: 1px solid {BORDER};
            padding: 12px;
            border-radius: 16px;
            box-shadow: 0 6px 18px rgba(0,0,0,0.05);
        }}

        div[data-testid="stMetricLabel"] {{
            color: {MUTED} !important;
            font-weight: 600;
        }}

        div[data-testid="stMetricValue"] {{
            color: {DARK} !important;
            font-weight: 800;
        }}

        .stTabs [data-baseweb="tab-list"] {{
            gap: 10px;
            flex-wrap: wrap;
        }}

        .stTabs [data-baseweb="tab"] {{
            height: 46px;
            padding-left: 18px;
            padding-right: 18px;
            border-radius: 12px;
            background: white;
            border: 1px solid {BORDER};
            color: {DARK} !important;
            font-weight: 600;
        }}

        .stTabs [aria-selected="true"] {{
            background: {PRIMARY} !important;
            color: white !important;
            border-color: {PRIMARY} !important;
        }}

        /* CLOSED SELECTBOX */
        div[data-baseweb="select"] > div {{
            background: {DROPDOWN_BG} !important;
            border-radius: 12px !important;
            color: white !important;
        }}

        div[data-baseweb="select"] > div * {{
            color: white !important;
            fill: white !important;
        }}

        div[data-baseweb="select"] span {{
            color: white !important;
        }}

        div[data-baseweb="select"] input {{
            color: white !important;
            -webkit-text-fill-color: white !important;
        }}

        div[data-baseweb="select"] svg {{
            fill: white !important;
        }}

        /* OPEN DROPDOWN MENU / POPOVER */
        div[data-baseweb="popover"] * {{
            color: white !important;
        }}

        div[data-baseweb="popover"] ul {{
            background: {DROPDOWN_BG} !important;
            color: white !important;
        }}

        div[data-baseweb="popover"] li {{
            background: {DROPDOWN_BG} !important;
            color: white !important;
        }}

        div[data-baseweb="popover"] li:hover {{
            background: #2b3145 !important;
            color: white !important;
        }}

        div[data-baseweb="popover"] li[aria-selected="true"] {{
            background: #343b52 !important;
            color: white !important;
        }}

        div[data-baseweb="popover"] li * {{
            color: white !important;
        }}

        ul[role="listbox"] {{
            background: {DROPDOWN_BG} !important;
            color: white !important;
        }}

        ul[role="listbox"] li {{
            background: {DROPDOWN_BG} !important;
            color: white !important;
        }}

        ul[role="listbox"] li:hover {{
            background: #2b3145 !important;
            color: white !important;
        }}

        ul[role="listbox"] li[aria-selected="true"] {{
            background: #343b52 !important;
            color: white !important;
        }}

        ul[role="listbox"] li * {{
            color: white !important;
        }}

        /* Inputs */
        input, textarea {{
            color: {DARK} !important;
        }}

        button {{
            color: {DARK} !important;
        }}

        [data-testid="stDataFrame"] {{
            border: 1px solid {BORDER};
            border-radius: 14px;
            overflow: hidden;
            background: white !important;
            box-shadow: 0 6px 18px rgba(0,0,0,0.05);
        }}

        [data-testid="stDataFrame"] * {{
            color: {TEXT} !important;
        }}

        table {{
            color: {TEXT} !important;
        }}

        section[data-testid="stSidebar"] * {{
            color: white !important;
        }}

        @media (max-width: 900px) {{
            .header-card {{
                padding: 16px;
                border-radius: 22px;
            }}
            .hero-logo-wrap {{
                min-height: auto;
                margin-bottom: 6px;
            }}
            .hero-logo-wrap img {{
                max-height: 72px;
            }}
            .hero-text-wrap {{
                min-height: auto;
            }}
            .block-container {{
                padding-left: 10px;
                padding-right: 10px;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def show_uniform_image(label: str, img_path: Path) -> None:
    img64 = image_to_base64(img_path)

    st.markdown('<div class="food-card">', unsafe_allow_html=True)

    if img64:
        ext = img_path.suffix.lower().replace(".", "")
        if ext == "jpg":
            ext = "jpeg"
        st.markdown(
            f"""
            <div class="food-img-box">
                <img src="data:image/{ext};base64,{img64}" alt="{label}">
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div class="food-img-box" style="display:flex;align-items:center;justify-content:center;color:#9CA3AF;font-weight:600;">
                Missing image
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(f'<div class="food-caption">{label}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


def build_forecast_chart(selected_item: str, hist: pd.DataFrame, fc: pd.DataFrame) -> go.Figure:
    hist_plot = hist.copy()
    fc_plot = fc.copy()

    hist_plot["week_end_date"] = pd.to_datetime(hist_plot["week_end_date"], errors="coerce")
    fc_plot["week_end_date"] = pd.to_datetime(fc_plot["week_end_date"], errors="coerce")

    hist_plot = hist_plot.dropna(subset=["week_end_date"])
    fc_plot = fc_plot.dropna(subset=["week_end_date"])

    fig = go.Figure()

    if not hist_plot.empty:
        fig.add_trace(
            go.Scatter(
                x=hist_plot["week_end_date"],
                y=hist_plot["weekly_qty"],
                mode="lines+markers",
                name="Historical",
                line=dict(color="#18243B", width=3),
                marker=dict(size=8, color="#E67E22"),
            )
        )

    if not fc_plot.empty:
        fig.add_trace(
            go.Scatter(
                x=fc_plot["week_end_date"],
                y=fc_plot["forecast_qty"],
                mode="lines+markers",
                name="Forecast",
                line=dict(color="#E67E22", width=3, dash="dash"),
                marker=dict(size=8, color="#F4D03F"),
            )
        )

    fig.update_layout(
        title=f"{selected_item} Demand Trend",
        title_font=dict(size=24, color="#18243B"),
        paper_bgcolor="rgba(255,255,255,0.95)",
        plot_bgcolor="rgba(255,255,255,0.92)",
        font=dict(color="#18243B"),
        height=680,
        margin=dict(l=20, r=20, t=70, b=20),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1.0,
            bgcolor="rgba(255,255,255,0.75)",
            font=dict(color="#18243B"),
        ),
    )

    fig.update_xaxes(
        title_text="Week ending date",
        showgrid=True,
        gridcolor="rgba(24,36,59,0.10)",
        color="#18243B",
        title_font=dict(color="#18243B"),
        tickfont=dict(color="#18243B"),
    )

    fig.update_yaxes(
        title_text="Units",
        showgrid=True,
        gridcolor="rgba(24,36,59,0.10)",
        color="#18243B",
        title_font=dict(color="#18243B"),
        tickfont=dict(color="#18243B"),
        rangemode="tozero",
    )

    return fig


st.set_page_config(
    page_title="NamasteLA Smart Inventory Dashboard",
    layout="wide"
)

inject_styles()

dfs = load_all_data()
show_missing_file_warning(dfs)

weekly_totals = dfs["Weekly totals"]
weekly_forecast = dfs["Weekly forecast"]
requirements = dfs["Component requirements"]
recommended_purchases = dfs["Recommended purchases"]
waste_log = dfs["Waste log"]

weekly_totals = format_date_only(weekly_totals, "week_end_date")
weekly_forecast = format_date_only(weekly_forecast, "week_end_date")
requirements = format_date_only(requirements, "week_end_date")
recommended_purchases = format_date_only(recommended_purchases, "week_end_date")
waste_log = format_date_only(waste_log, "week_end_date")

weekly_totals = round_display_columns(weekly_totals, ["weekly_qty"])
weekly_forecast = round_display_columns(weekly_forecast, ["forecast_qty"])
requirements = round_display_columns(requirements, ["required_qty"])
recommended_purchases = round_display_columns(
    recommended_purchases,
    ["required_qty", "safety_stock", "on_hand_qty", "recommended_purchase_qty"],
)
waste_log = round_display_columns(waste_log, ["waste_qty_units", "estimated_cost"])

st.sidebar.markdown(f"## {COMPANY_NAME}")
st.sidebar.write("Food Forecasting & Inventory Planning")
if st.sidebar.button("Reload Data"):
    st.cache_data.clear()

st.markdown('<div class="top-accent-bar"></div>', unsafe_allow_html=True)
st.markdown('<div class="header-card">', unsafe_allow_html=True)

hero_left, hero_right = st.columns([1, 4.8], vertical_alignment="center")

with hero_left:
    if LOGO_PATH.exists():
        st.markdown('<div class="hero-logo-wrap">', unsafe_allow_html=True)
        st.image(str(LOGO_PATH), use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

with hero_right:
    st.markdown('<div class="hero-text-wrap">', unsafe_allow_html=True)
    st.markdown('<div class="hero-tag">Smart Forecasting and Purchase Planning</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="hero-title">{COMPANY_NAME} Smart Inventory Dashboard</div>', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="hero-sub">
            Forecast weekend demand, convert it into ingredient and packaging needs,
            and generate a clean purchase plan for operations and procurement.
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

tabs = st.tabs([
    "Overview",
    "Forecast",
    "Requirements",
    "Purchase Plan",
    "Waste"
])

with tabs[0]:
    st.markdown('<div class="section-title">Overview</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Quick summary of current planning outputs</div>', unsafe_allow_html=True)

    if not weekly_totals.empty:
        total_units = int(weekly_totals["weekly_qty"].sum())
        total_items = int(weekly_totals["item"].nunique())
    else:
        total_units = 0
        total_items = 0

    if not recommended_purchases.empty:
        buy_count = int((recommended_purchases["recommended_purchase_qty"] > 0).sum())
        total_buy_qty = int(recommended_purchases["recommended_purchase_qty"].sum())
    else:
        buy_count = 0
        total_buy_qty = 0

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(f'<div class="kpi-card"><div class="kpi-label">Total historical units</div><div class="kpi-value">{total_units}</div></div>', unsafe_allow_html=True)
    with k2:
        st.markdown(f'<div class="kpi-card"><div class="kpi-label">Items tracked</div><div class="kpi-value">{total_items}</div></div>', unsafe_allow_html=True)
    with k3:
        st.markdown(f'<div class="kpi-card"><div class="kpi-label">Components to buy</div><div class="kpi-value">{buy_count}</div></div>', unsafe_allow_html=True)
    with k4:
        st.markdown(f'<div class="kpi-card"><div class="kpi-label">Total recommended quantity</div><div class="kpi-value">{total_buy_qty}</div></div>', unsafe_allow_html=True)

    st.write("")

    st.markdown('<div class="panel-title">Next Planned Purchase List</div>', unsafe_allow_html=True)
    st.markdown('<div class="panel-sub">Recommended buying list for the upcoming market cycle</div>', unsafe_allow_html=True)

    if not recommended_purchases.empty:
        next_week = recommended_purchases["week_end_date"].min()
        st.caption(f"Planning week ending: {next_week}")

        preview = recommended_purchases.copy()
        preview = preview[preview["recommended_purchase_qty"] > 0]
        preview = preview.sort_values(["component_type", "component"])
        st.dataframe(preview, use_container_width=True, hide_index=True)
    else:
        st.info("No purchase recommendations available yet.")

    st.write("")

    st.markdown('<div class="panel-title">Featured Menu</div>', unsafe_allow_html=True)
    st.markdown('<div class="panel-sub">Highlighted products from the NamasteLA menu</div>', unsafe_allow_html=True)

    menu_items = [
        ("Chickpea Meal plate", IMAGE_MAP["Chickpea Meal plate"]),
        ("Paneer Meal plate", IMAGE_MAP["Paneer Meal plate"]),
        ("Pani Puri 5 Balls", IMAGE_MAP["Pani Puri 5 Balls"]),
        ("Pepsi Lemonade", IMAGE_MAP["Pepsi Lemonade"]),
        ("Red KidneyBean Plate", IMAGE_MAP["Red KidneyBean Plate"]),
        ("Lentil soup", IMAGE_MAP["Lentil soup"]),
        ("Strawberry yogurt", IMAGE_MAP["Strawberry yogurt"]),
        ("Pani Puri 12 Balls", IMAGE_MAP["Pani Puri 12 Balls"]),
    ]

    if "menu_start_idx" not in st.session_state:
        st.session_state.menu_start_idx = 0

    start = st.session_state.menu_start_idx
    visible_items = menu_items[start:start + 4]

    left_nav, c1, c2, c3, c4, right_nav = st.columns([0.45, 1, 1, 1, 1, 0.45])

    with left_nav:
        st.markdown('<div class="nav-btn-wrap">', unsafe_allow_html=True)
        if st.button("◀", key="menu_prev_side"):
            st.session_state.menu_start_idx = max(0, st.session_state.menu_start_idx - 4)
        st.markdown('</div>', unsafe_allow_html=True)

    for col, item in zip([c1, c2, c3, c4], visible_items):
        with col:
            show_uniform_image(item[0], item[1])

    with right_nav:
        st.markdown('<div class="nav-btn-wrap">', unsafe_allow_html=True)
        if st.button("▶", key="menu_next_side"):
            max_start = max(0, len(menu_items) - 4)
            st.session_state.menu_start_idx = min(max_start, st.session_state.menu_start_idx + 4)
        st.markdown('</div>', unsafe_allow_html=True)

with tabs[1]:
    st.markdown('<div class="section-title">Forecast</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Historical weekly totals and forecasted item demand</div>', unsafe_allow_html=True)

    if weekly_totals.empty or weekly_forecast.empty:
        st.info("Forecast files are not ready yet.")
    else:
        items = sorted(weekly_totals["item"].dropna().unique().tolist())
        selected_item = st.selectbox("Select item", items, key="forecast_item_select")

        set_forecast_background(selected_item)

        hist = weekly_totals[weekly_totals["item"] == selected_item].copy()
        fc = weekly_forecast[weekly_forecast["item"] == selected_item].copy()

        if "method" in fc.columns:
            fc = fc.drop(columns=["method"])

        if "weekly_qty" in hist.columns:
            hist = hist[hist["weekly_qty"] > 0]

        hist = hist.sort_values("week_end_date")
        fc = fc.sort_values("week_end_date")

        left_col, right_col = st.columns([0.95, 1.25], gap="large")

        with left_col:
            st.markdown("### Historical Weekly Totals")
            st.dataframe(
                hist,
                use_container_width=True,
                hide_index=True,
                height=315
            )

            st.markdown("### Forecast for Upcoming Weeks")
            st.dataframe(
                fc,
                use_container_width=True,
                hide_index=True,
                height=315
            )

        with right_col:
            fig = build_forecast_chart(selected_item, hist, fc)
            st.plotly_chart(fig, use_container_width=True)

with tabs[2]:
    st.markdown('<div class="section-title">Requirements</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Ingredient and packaging quantities needed for the selected week</div>', unsafe_allow_html=True)

    if requirements.empty:
        st.info("Requirements file is not ready yet.")
    else:
        weeks = sorted(requirements["week_end_date"].dropna().unique().tolist())
        selected_week = st.selectbox("Select planning week", weeks, key="requirements_week_select")

        req_filtered = requirements[requirements["week_end_date"] == selected_week].copy()

        component_types = sorted(req_filtered["component_type"].dropna().unique().tolist())
        selected_types = st.multiselect(
            "Filter by component type",
            component_types,
            default=component_types,
            key="requirements_type_filter"
        )

        req_filtered = req_filtered[req_filtered["component_type"].isin(selected_types)]
        req_filtered = req_filtered.sort_values(["component_type", "component"])

        st.dataframe(req_filtered, use_container_width=True, hide_index=True)

with tabs[3]:
    st.markdown('<div class="section-title">Purchase Plan</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Final recommended procurement quantities after inventory check</div>', unsafe_allow_html=True)

    if recommended_purchases.empty:
        st.info("Recommended purchases file is not ready yet.")
    else:
        weeks = sorted(recommended_purchases["week_end_date"].dropna().unique().tolist())
        selected_week = st.selectbox("Select planning week", weeks, key="purchase_week_select")

        purchase_filtered = recommended_purchases[
            recommended_purchases["week_end_date"] == selected_week
        ].copy()

        show_only_to_buy = st.checkbox(
            "Show only items that need to be purchased",
            value=True,
            key="purchase_checkbox"
        )

        if show_only_to_buy:
            purchase_filtered = purchase_filtered[
                purchase_filtered["recommended_purchase_qty"] > 0
            ]

        purchase_filtered = purchase_filtered.sort_values(["component_type", "component"])
        st.dataframe(purchase_filtered, use_container_width=True, hide_index=True)

        csv_data = purchase_filtered.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download Purchase List as CSV",
            data=csv_data,
            file_name=f"recommended_purchases_{selected_week}.csv",
            mime="text/csv"
        )

with tabs[4]:
    st.markdown('<div class="section-title">Waste</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Waste summary and waste log tracking</div>', unsafe_allow_html=True)

    if waste_log.empty:
        st.info("Waste log is not available yet.")
    else:
        total_waste_units = int(waste_log["waste_qty_units"].sum()) if "waste_qty_units" in waste_log.columns else 0
        total_waste_cost = int(waste_log["estimated_cost"].sum()) if "estimated_cost" in waste_log.columns else 0

        c1, c2 = st.columns(2)
        c1.metric("Total waste units", total_waste_units)
        c2.metric("Estimated waste cost", f"${total_waste_cost}")

        st.markdown("### Waste Log Details")
        st.dataframe(
            waste_log.sort_values(["week_end_date", "item"]),
            use_container_width=True,
            hide_index=True
        )
