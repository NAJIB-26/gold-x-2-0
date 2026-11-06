"""واجهة GOLD-X 2.0 العربية."""

import json
from datetime import datetime, timezone

import pandas as pd
import plotly.graph_objects as go
import streamlit as st  # type: ignore[reportMissingImports]

from data_fetcher import fetch_live_data  # type: ignore[reportMissingImports]
from model import gold_x_model  # type: ignore[reportMissingImports]


st.set_page_config(
    page_title="GOLD-X 2.0 — نظام توقع الذهب",
    page_icon="🥇",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Arabic:wght@400;500;600;700&display=swap');
    :root { --gold:#D8B45A; --ink:#080B12; --muted:#94A3B8; --line:rgba(216,180,90,.18); }
    html, body, [class*="css"] { font-family:'IBM Plex Sans Arabic', sans-serif; }
    .stApp { background: radial-gradient(circle at 80% -10%, rgba(216,180,90,.11), transparent 32%), #080B12; }
    .block-container { max-width: 1240px; padding-top: 2.3rem; padding-bottom: 3rem; }
    [data-testid="stHeader"] { background: transparent; }
    [data-testid="stMetric"] { background: linear-gradient(145deg, rgba(17,24,39,.95), rgba(10,14,23,.92)); border:1px solid var(--line); border-radius:18px; padding:1rem 1.15rem; box-shadow:0 16px 45px rgba(0,0,0,.18); }
    [data-testid="stMetricLabel"] { color:#A8B4C7; }
    [data-testid="stMetricValue"] { color:#F8FAFC; font-weight:700; }
    .hero { display:flex; justify-content:space-between; align-items:flex-end; gap:2rem; padding:1.7rem 0 1.35rem; border-bottom:1px solid rgba(148,163,184,.14); margin-bottom:1.25rem; }
    .eyebrow { color:var(--gold); font-size:.78rem; letter-spacing:.12em; text-transform:uppercase; font-weight:700; }
    .hero h1 { margin:.25rem 0 .35rem; font-size:clamp(2rem,4vw,3.4rem); line-height:1.12; letter-spacing:-.04em; }
    .hero p { color:var(--muted); margin:0; font-size:1.02rem; }
    .stamp { color:#CBD5E1; font-size:.78rem; border:1px solid rgba(148,163,184,.2); border-radius:999px; padding:.5rem .8rem; white-space:nowrap; }
    .section-kicker { display:flex; align-items:center; gap:.6rem; color:#F8FAFC; font-weight:700; font-size:1.05rem; margin:1.55rem 0 .75rem; }
    .section-kicker:before { content:''; width:8px; height:8px; border-radius:50%; background:var(--gold); box-shadow:0 0 14px var(--gold); }
    .regime { display:inline-flex; align-items:center; gap:.5rem; border-radius:999px; padding:.5rem .9rem; margin-bottom:.4rem; font-weight:700; font-size:.95rem; }
    .regime-normal { color:#76E3A6; background:rgba(34,197,94,.1); border:1px solid rgba(34,197,94,.25); }
    .regime-stress { color:#FDBA74; background:rgba(249,115,22,.1); border:1px solid rgba(249,115,22,.25); }
    .regime-crisis { color:#FDA4AF; background:rgba(244,63,94,.1); border:1px solid rgba(244,63,94,.25); }
    .radar-box { border-radius:18px; padding:1.15rem 1.25rem; margin:.35rem 0 1rem; }
    .radar-critical { background:rgba(244,63,94,.08); border:1px solid rgba(244,63,94,.3); }
    .radar-warning { background:rgba(249,115,22,.08); border:1px solid rgba(249,115,22,.3); }
    .radar-clear { background:rgba(34,197,94,.08); border:1px solid rgba(34,197,94,.25); }
    .radar-title { font-weight:700; font-size:1.08rem; margin-bottom:.35rem; }
    .radar-copy { color:#CBD5E1; margin:0; line-height:1.8; }
    .footnote { color:#64748B; font-size:.78rem; border-top:1px solid rgba(148,163,184,.12); padding-top:1rem; margin-top:2rem; }
    .small-muted { color:#94A3B8; font-size:.82rem; }
    div.stButton > button { border:1px solid rgba(216,180,90,.45); color:#F8FAFC; background:rgba(216,180,90,.08); border-radius:12px; font-weight:600; }
    div.stButton > button:hover { border-color:var(--gold); color:var(--gold); }
    </style>
    <div dir="rtl">
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero" dir="rtl">
      <div>
        <div class="eyebrow">GOLD-X / MARKET INTELLIGENCE</div>
        <h1>🥇 GOLD-X 2.0</h1>
        <p>نظام توقع الذهب — نموذج متعدد الطبقات: اقتصادي + تدفقات + ذكاء اصطناعي</p>
      </div>
      <div class="stamp">بيانات Yahoo Finance · تحديث عند الطلب</div>
    </div>
    """,
    unsafe_allow_html=True,
)

@st.cache_data(ttl=300, show_spinner=False)
def load_market_data():
    """يحد من الطلبات المتكررة مع إبقاء زر التحديث متاحاً للمستخدم."""
    return fetch_live_data()


with st.spinner("جاري جلب البيانات الحية..."):
    raw_data = load_market_data()

if raw_data is None:
    st.error("تعذر جلب بيانات السوق حالياً. تحقق من الاتصال ثم أعد المحاولة.")
    st.stop()

assert raw_data is not None
result = gold_x_model(raw_data)

col1, col2, col3 = st.columns(3)
with col1:
    st.metric(
        "السعر الحالي",
        f"${raw_data['current_price']:,.0f}",
        delta=f"{raw_data['price_change'] * 100:+.2f}%",
    )
with col2:
    st.metric(
        "السعر المتوقع",
        f"${result['predicted_price']:,.0f}",
        delta=f"{result['change_pct'] * 100:+.2f}%",
    )
with col3:
    st.metric("درجة الثقة", f"{result['confidence']:.1f}/10")

regime_meta = {
    "NORMAL": ("🟢", "حالة السوق: NORMAL", "regime-normal"),
    "STRESS": ("🟠", "حالة السوق: STRESS", "regime-stress"),
    "CRISIS": ("🔴", "حالة السوق: CRISIS", "regime-crisis"),
}
regime_icon, regime_label, regime_class = regime_meta[result["regime"]]
st.markdown(
    f'<div class="section-kicker">قراءة الحالة</div><div class="regime {regime_class}">{regime_icon} {regime_label}</div>',
    unsafe_allow_html=True,
)
st.info(result["recommendation"])

st.markdown('<div class="section-kicker">📡 رادار البيع القسري</div>', unsafe_allow_html=True)
radar = result["radar"]
radar_class = {"CRITICAL": "radar-critical", "WARNING": "radar-warning", "CLEAR": "radar-clear"}[radar["status"]]
radar_icon = {"CRITICAL": "⛔", "WARNING": "⚠️", "CLEAR": "✅"}[radar["status"]]
st.markdown(
    f'<div class="radar-box {radar_class}" dir="rtl"><div class="radar-title">{radar_icon} {radar["status"]} · {radar["score"]}/10</div><p class="radar-copy">{radar["msg"]}</p></div>',
    unsafe_allow_html=True,
)

if result["warnings"]:
    st.markdown('<div class="section-kicker">⚠️ الإنذارات المبكرة</div>', unsafe_allow_html=True)
    for warning in result["warnings"]:
        st.warning(warning)

st.markdown('<div class="section-kicker">🔍 تفصيل العوامل</div>', unsafe_allow_html=True)
chart_data = pd.DataFrame(
    {
        "العامل": ["اقتصادي", "تدفقات", "ذكاء اصطناعي"],
        "القيمة": [
            result["breakdown"]["economic"] * 100,
            result["breakdown"]["flow"] * 100,
            result["breakdown"]["ai"] * 100,
        ],
        "اللون": ["#4CAF50", "#FF9800", "#2196F3"],
    }
)
fig = go.Figure(
    go.Bar(
        x=chart_data["العامل"],
        y=chart_data["القيمة"],
        marker_color=chart_data["اللون"],
        text=[f"{value:+.2f}%" for value in chart_data["القيمة"]],
        textposition="outside",
        hovertemplate="%{x}: %{y:.2f}%<extra></extra>",
    )
)
fig.update_layout(
    height=330,
    margin=dict(l=10, r=10, t=20, b=10),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="IBM Plex Sans Arabic", color="#CBD5E1"),
    yaxis=dict(title="المساهمة النسبية (%)", gridcolor="rgba(148,163,184,.12)", zerolinecolor="rgba(216,180,90,.35)"),
    xaxis=dict(showgrid=False),
    showlegend=False,
)
st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

with st.expander("📊 البيانات الخام المستخدمة"):
    st.json(json.loads(json.dumps(raw_data, default=float)))

refresh_col, update_col = st.columns([1, 3])
with refresh_col:
    if st.button("🔄 تحديث البيانات", use_container_width=True):
        load_market_data.clear()  # type: ignore[attr-defined]
        st.rerun()
with update_col:
    updated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    st.markdown(f'<div class="small-muted" style="padding:.65rem 0">آخر طلب تحديث: {updated}</div>', unsafe_allow_html=True)

st.markdown(
    '<div class="footnote">⚠️ هذا النموذج أداة مساعدة للتفكير، وليس نصيحة استثمارية. الأسواق متغيرة والنتائج التقديرية ليست ضماناً للأداء المستقبلي.</div></div>',
    unsafe_allow_html=True,
)
