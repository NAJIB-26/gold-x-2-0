"""واجهة GOLD-X 2.0 العربية مع طبقة تعريفية وتجهيزات نمو آمنة."""

import json
import re
from datetime import datetime, timezone

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st  # type: ignore[reportMissingImports]

from data_fetcher import fetch_live_data  # type: ignore[reportMissingImports]
from model import gold_x_model  # type: ignore[reportMissingImports]

GLOBAL_CURRENCIES = {
    "USD": "الدولار الأمريكي", "EUR": "اليورو", "GBP": "الجنيه الإسترليني",
    "JPY": "الين الياباني", "CNY": "اليوان الصيني", "CHF": "الفرنك السويسري",
    "CAD": "الدولار الكندي", "AUD": "الدولار الأسترالي", "INR": "الروبية الهندية",
    "SGD": "الدولار السنغافوري",
}
ARAB_CURRENCIES = {
    "AED": "الدرهم الإماراتي", "BHD": "الدينار البحريني", "DZD": "الدينار الجزائري",
    "DJF": "الفرنك الجيبوتي", "EGP": "الجنيه المصري", "IQD": "الدينار العراقي",
    "JOD": "الدينار الأردني", "KWD": "الدينار الكويتي", "LBP": "الليرة اللبنانية",
    "LYD": "الدينار الليبي", "MAD": "الدرهم المغربي", "MRU": "الأوقية الموريتانية",
    "OMR": "الريال العُماني", "QAR": "الريال القطري", "SAR": "الريال السعودي",
    "SDG": "الجنيه السوداني", "SOS": "الشلن الصومالي", "SYP": "الليرة السورية",
    "TND": "الدينار التونسي", "YER": "الريال اليمني", "KMF": "الفرنك القمري",
    "ILS": "الشيكل المستخدم في فلسطين",
}
CURRENCY_NAMES = {**GLOBAL_CURRENCIES, **ARAB_CURRENCIES}
CURRENCY_SYMBOLS = {
    "USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥", "CNY": "¥", "CHF": "CHF",
    "CAD": "C$", "AUD": "A$", "INR": "₹", "SGD": "S$", "AED": "د.إ", "BHD": "د.ب",
    "DZD": "دج", "DJF": "Fdj", "EGP": "ج.م", "IQD": "ع.د", "JOD": "د.أ",
    "KWD": "د.ك", "LBP": "ل.ل", "LYD": "ل.د", "MAD": "د.م", "MRU": "أوقية",
    "OMR": "ر.ع", "QAR": "ر.ق", "SAR": "ر.س", "SDG": "ج.س", "SOS": "ش.ص",
    "SYP": "ل.س", "TND": "د.ت", "YER": "ر.ي", "KMF": "KMF", "ILS": "₪",
}

st.set_page_config(page_title="GOLD-X 2.0 — نظام توقع الذهب", page_icon="🥇", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Arabic:wght@400;500;600;700&display=swap');
:root { --gold:#D8B45A; --muted:#94A3B8; --line:rgba(216,180,90,.18); }
html, body, [class*="css"] { font-family:'IBM Plex Sans Arabic', sans-serif; }
.stApp { background: radial-gradient(circle at 80% -10%, rgba(216,180,90,.11), transparent 32%), #080B12; }
.block-container { max-width:1240px; padding-top:2.3rem; padding-bottom:3rem; }
[data-testid="stHeader"] { background:transparent; }
[data-testid="stMetric"] { background:linear-gradient(145deg,rgba(17,24,39,.95),rgba(10,14,23,.92)); border:1px solid var(--line); border-radius:18px; padding:1rem 1.15rem; box-shadow:0 16px 45px rgba(0,0,0,.18); }
[data-testid="stMetricLabel"] { color:#A8B4C7; } [data-testid="stMetricValue"] { color:#F8FAFC; font-weight:700; }
.hero { display:flex; justify-content:space-between; align-items:flex-end; gap:2rem; padding:1.7rem 0 1.35rem; border-bottom:1px solid rgba(148,163,184,.14); margin-bottom:1.25rem; }
.eyebrow { color:var(--gold); font-size:.78rem; letter-spacing:.12em; text-transform:uppercase; font-weight:700; }
.hero h1 { margin:.25rem 0 .35rem; font-size:clamp(2rem,4vw,3.4rem); line-height:1.12; } .hero p { color:var(--muted); margin:0; font-size:1.02rem; }
.stamp { color:#CBD5E1; font-size:.78rem; border:1px solid rgba(148,163,184,.2); border-radius:999px; padding:.5rem .8rem; white-space:nowrap; }
.section-kicker { display:flex; align-items:center; gap:.6rem; color:#F8FAFC; font-weight:700; font-size:1.05rem; margin:1.55rem 0 .75rem; }
.section-kicker:before { content:''; width:8px; height:8px; border-radius:50%; background:var(--gold); box-shadow:0 0 14px var(--gold); }
.regime { display:inline-flex; align-items:center; gap:.5rem; border-radius:999px; padding:.5rem .9rem; margin-bottom:.4rem; font-weight:700; font-size:.95rem; }
.regime-normal { color:#76E3A6; background:rgba(34,197,94,.1); border:1px solid rgba(34,197,94,.25); } .regime-stress { color:#FDBA74; background:rgba(249,115,22,.1); border:1px solid rgba(249,115,22,.25); } .regime-crisis { color:#FDA4AF; background:rgba(244,63,94,.1); border:1px solid rgba(244,63,94,.25); }
.radar-box { border-radius:18px; padding:1.15rem 1.25rem; margin:.35rem 0 1rem; } .radar-critical { background:rgba(244,63,94,.08); border:1px solid rgba(244,63,94,.3); } .radar-warning { background:rgba(249,115,22,.08); border:1px solid rgba(249,115,22,.3); } .radar-clear { background:rgba(34,197,94,.08); border:1px solid rgba(34,197,94,.25); }
.radar-title { font-weight:700; font-size:1.08rem; margin-bottom:.35rem; } .radar-copy { color:#CBD5E1; margin:0; line-height:1.8; }
.growth-card { border:1px solid rgba(216,180,90,.22); border-radius:18px; padding:1.1rem 1.25rem; background:linear-gradient(145deg,rgba(216,180,90,.09),rgba(15,23,42,.52)); height:100%; } .growth-card h3 { margin:.1rem 0 .45rem; color:#F8FAFC; } .growth-card p { color:#CBD5E1; line-height:1.8; margin:0; }
.small-muted { color:#94A3B8; font-size:.82rem; } .footnote { color:#64748B; font-size:.78rem; border-top:1px solid rgba(148,163,184,.12); padding-top:1rem; margin-top:2rem; line-height:1.8; }
div.stButton > button { border:1px solid rgba(216,180,90,.45); color:#F8FAFC; background:rgba(216,180,90,.08); border-radius:12px; font-weight:600; } div.stButton > button:hover { border-color:var(--gold); color:var(--gold); }
</style><div dir="rtl">""", unsafe_allow_html=True)
st.markdown("""<div class="hero" dir="rtl"><div><div class="eyebrow">GOLD-X / MARKET INTELLIGENCE</div><h1>🥇 GOLD-X 2.0</h1><p>نظام توقع الذهب — نموذج متعدد الطبقات: اقتصادي + تدفقات + ذكاء اصطناعي</p></div><div class="stamp">بيانات Yahoo Finance · تحديث عند الطلب</div></div>""", unsafe_allow_html=True)
st.markdown('<div class="section-kicker">عن المنصة</div>', unsafe_allow_html=True)
intro_col, interest_col = st.columns([1.45, 1])
with intro_col:
    st.markdown('<div class="growth-card" dir="rtl"><h3>قراءة أوضح لسوق الذهب</h3><p>استكشف السعر الحالي والتوقعات والعوامل المؤثرة مجاناً. GOLD-X أداة تحليلية وليست وعداً بالربح أو بديلاً عن مستشار مالي.</p></div>', unsafe_allow_html=True)
with interest_col:
    st.markdown("**ما الذي يهمك أكثر؟**")
    interest = st.selectbox("اختر اهتماماً واحداً (يُحفظ لهذه الجلسة فقط)", ["تحليل يومي للذهب", "العوامل الاقتصادية", "رادار المخاطر", "تعلم قراءة السوق"], label_visibility="collapsed")
    st.caption(f"اختيارك الحالي: {interest}. لا يتم إرسال هذا الاختيار أو تخزينه خارج الجلسة.")

@st.cache_data(ttl=300, show_spinner=False)
def load_market_data():
    return fetch_live_data()

@st.cache_data(ttl=1800, show_spinner=False)
def load_fx_rates():
    try:
        response = requests.get("https://open.er-api.com/v6/latest/USD", timeout=8)
        response.raise_for_status()
        rates = response.json().get("rates", {})
        rates["USD"] = 1.0
        return {code: float(rates[code]) for code in CURRENCY_NAMES if code in rates}
    except Exception:
        return {"USD": 1.0}

with st.spinner("جاري جلب البيانات الحية..."): raw_data = load_market_data()
if raw_data is None:
    st.error("تعذر جلب سعر الذهب من المصدر الأساسي والاحتياطي. تحقق من الاتصال ثم أعد المحاولة لاحقاً.")
    st.stop()
quality = raw_data.get("data_quality", "unknown")
quality_labels = {"live":"بيانات مباشرة من المصدر الأساسي", "partial":"بيانات جزئية: بعض المؤشرات تستخدم قيماً افتراضية", "fallback":"بيانات احتياطية: سعر الذهب من مصدر بديل", "unknown":"حالة المصدر غير محددة"}
if quality == "live": st.success(f"{quality_labels[quality]} · {raw_data.get('data_source', 'غير محدد')} · {raw_data.get('updated_at_utc', '')}")
else: st.warning(f"{quality_labels.get(quality, quality)} · {raw_data.get('data_source', 'غير محدد')} · {raw_data.get('updated_at_utc', '')}")
for data_warning in raw_data.get("data_warnings", []): st.caption(f"تنبيه مصدر البيانات: {data_warning}")
result = gold_x_model(raw_data)
col1, col2, col3 = st.columns(3)
with col1: st.metric("السعر الحالي", f"${raw_data['current_price']:,.0f}", delta=f"{raw_data['price_change'] * 100:+.2f}%")
with col2: st.metric("السعر المتوقع", f"${result['predicted_price']:,.0f}", delta=f"{result['change_pct'] * 100:+.2f}%")
with col3: st.metric("درجة الثقة", f"{result['confidence']:.1f}/10")

st.markdown('<div class="section-kicker">💱 محول أسعار الذهب</div>', unsafe_allow_html=True)
currency_options = list(GLOBAL_CURRENCIES) + [code for code in ARAB_CURRENCIES if code not in GLOBAL_CURRENCIES]
currency_col, fx_note_col = st.columns([1, 2])
with currency_col:
    selected_currency = st.selectbox("اختر العملة", currency_options, format_func=lambda code: f"{code} — {CURRENCY_NAMES[code]}", key="gold_currency")
selected_currency = str(selected_currency)
fx_rates = load_fx_rates()
fx_rate = float(fx_rates.get(selected_currency, 1.0))
with fx_note_col:
    if selected_currency not in fx_rates: st.warning("تعذر تحديث سعر الصرف لهذه العملة؛ عُرضت القيم بالدولار حتى عودة المصدر.")
    else: st.caption(f"سعر الصرف التقريبي: 1 USD = {fx_rate:,.4g} {selected_currency} · تحديث الصرف كل 30 دقيقة")
ounce_usd = float(raw_data["current_price"])
gram24_usd = ounce_usd / 31.1034768
gold_prices_usd = {"الأونصة التروية": ounce_usd, "جرام عيار 24": gram24_usd, "جرام عيار 21": gram24_usd * 21 / 24, "جرام عيار 18": gram24_usd * 18 / 24, "الجنيه الذهب عيار 21 (8 جرام)": gram24_usd * 21 / 24 * 8}
currency_symbol = CURRENCY_SYMBOLS.get(selected_currency, selected_currency)
price_cols = st.columns(5)
for price_col, (label, price_usd) in zip(price_cols, gold_prices_usd.items()):
    with price_col: st.metric(label, f"{currency_symbol} {price_usd * fx_rate:,.2f}")
st.caption("الأسعار محسوبة من سعر الذهب الخام ولا تشمل المصنعية أو الضريبة أو هامش التاجر أو فروق سعر الصرف المحلية. وزن الجنيه المستخدم 8 جرام من عيار 21.")

regime_meta = {"NORMAL": ("🟢", "حالة السوق: NORMAL", "regime-normal"), "STRESS": ("🟠", "حالة السوق: STRESS", "regime-stress"), "CRISIS": ("🔴", "حالة السوق: CRISIS", "regime-crisis")}
regime_icon, regime_label, regime_class = regime_meta[result["regime"]]
st.markdown(f'<div class="section-kicker">قراءة الحالة</div><div class="regime {regime_class}">{regime_icon} {regime_label}</div>', unsafe_allow_html=True)
st.info(result["recommendation"])
st.markdown('<div class="section-kicker">📡 رادار البيع القسري</div>', unsafe_allow_html=True)
radar = result["radar"]
radar_class = {"CRITICAL":"radar-critical", "WARNING":"radar-warning", "CLEAR":"radar-clear"}[radar["status"]]
radar_icon = {"CRITICAL":"⛔", "WARNING":"⚠️", "CLEAR":"✅"}[radar["status"]]
st.markdown(f'<div class="radar-box {radar_class}" dir="rtl"><div class="radar-title">{radar_icon} {radar["status"]} · {radar["score"]}/10</div><p class="radar-copy">{radar["msg"]}</p></div>', unsafe_allow_html=True)
if result["warnings"]:
    st.markdown('<div class="section-kicker">⚠️ الإنذارات المبكرة</div>', unsafe_allow_html=True)
    for warning in result["warnings"]: st.warning(warning)
st.markdown('<div class="section-kicker">🔍 تفصيل العوامل</div>', unsafe_allow_html=True)
chart_data = pd.DataFrame({"العامل":["اقتصادي","تدفقات","ذكاء اصطناعي"], "القيمة":[result["breakdown"]["economic"]*100, result["breakdown"]["flow"]*100, result["breakdown"]["ai"]*100], "اللون":["#4CAF50","#FF9800","#2196F3"]})
fig = go.Figure(go.Bar(x=chart_data["العامل"], y=chart_data["القيمة"], marker_color=chart_data["اللون"], text=[f"{value:+.2f}%" for value in chart_data["القيمة"]], textposition="outside", hovertemplate="%{x}: %{y:.2f}%<extra></extra>"))
fig.update_layout(height=330, margin=dict(l=10,r=10,t=20,b=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(family="IBM Plex Sans Arabic", color="#CBD5E1"), yaxis=dict(title="المساهمة النسبية (%)", gridcolor="rgba(148,163,184,.12)", zerolinecolor="rgba(216,180,90,.35)"), xaxis=dict(showgrid=False), showlegend=False)
st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
with st.expander("📊 البيانات الخام المستخدمة"): st.json(json.loads(json.dumps(raw_data, default=float)))
refresh_col, update_col = st.columns([1, 3])
with refresh_col:
    if st.button("🔄 تحديث البيانات", use_container_width=True):
        load_market_data.clear()
        load_fx_rates.clear()
        st.rerun()
with update_col:
    updated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    st.markdown(f'<div class="small-muted" style="padding:.65rem 0">آخر طلب تحديث: {updated}</div>', unsafe_allow_html=True)
st.markdown('<div class="section-kicker">📬 نشرة GOLD-X</div>', unsafe_allow_html=True)
st.write("احصل مستقبلاً على ملخصات السوق الأسبوعية. هذا النموذج لا يرسل أو يحفظ البريد حالياً؛ أضف مزود نشرة بعد اختيار سياسة الخصوصية وموافقة المستخدم.")
with st.form("newsletter_interest_form", clear_on_submit=True):
    email = st.text_input("البريد الإلكتروني (اختياري)", placeholder="name@example.com")
    consent = st.checkbox("أوافق على استخدام البريد للاشتراك في النشرة عند تفعيلها")
    submitted = st.form_submit_button("تسجيل الاهتمام")
if submitted:
    if not consent: st.warning("يرجى تفعيل الموافقة أولاً. لم يتم حفظ أي بيانات.")
    elif not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email.strip()): st.warning("أدخل بريداً إلكترونياً صحيحاً. لم يتم حفظ أي بيانات.")
    else: st.success("تم تسجيل اهتمامك لهذه الجلسة فقط. لم يُحفظ البريد لأن خدمة النشرة لم تُربط بعد.")
st.markdown('<div class="section-kicker">🚀 ما القادم؟</div>', unsafe_allow_html=True)
free_col, premium_col, partner_col = st.columns(3)
with free_col: st.markdown("<div class='growth-card' dir='rtl'><h3>الخطة المجانية</h3><p>بيانات السوق والتحليل الأساسي والتحديث عند الطلب متاحة للزوار دون تسجيل دخول.</p></div>", unsafe_allow_html=True)
with premium_col: st.markdown("<div class='growth-card' dir='rtl'><h3>Premium قريباً</h3><p>قد تشمل تقارير دورية وتنبيهات وسجل أداء النموذج بعد إضافة حسابات ودفع آمن. لا توجد مدفوعات مفعّلة حالياً.</p></div>", unsafe_allow_html=True)
with partner_col: st.markdown("<div class='growth-card' dir='rtl'><h3>رعاية وشراكات</h3><p>هذه مساحة مهيأة لرعاية أو رابط تابع بعد مراجعة الجهة والإفصاح عنه بوضوح. لا توجد إعلانات أو روابط تداول مفعّلة حالياً.</p></div>", unsafe_allow_html=True)
st.markdown('<div class="footnote">⚠️ هذا النموذج أداة مساعدة للتفكير، وليس نصيحة استثمارية. الأسواق متغيرة والنتائج التقديرية ليست ضماناً للأداء المستقبلي. لا يتم جمع بيانات شخصية أو حفظ البريد في هذه النسخة.</div></div>', unsafe_allow_html=True)
