"""واجهة GOLD-X 2.0 العربية مع طبقة تعريفية وتجهيزات نمو آمنة."""

import json
import re
from datetime import datetime, timezone

import pandas as pd
import plotly.graph_objects as go
import streamlit as st  # type: ignore[reportMissingImports]

from data_fetcher import fetch_live_data  # type: ignore[reportMissingImports]
from model import gold_x_model  # type: ignore[reportMissingImports]
from advanced_layers import advanced_summary, build_advanced_snapshot, fetch_optional_market_data


NEWS_ITEMS = [
    ("إحصاءات مشتريات البنوك المركزية", "World Gold Council", "طلب مؤسسي", "https://www.gold.org/goldhub/gold-focus/2026/11/central-bank-gold-statistics-september-2026", "متابعة مشتريات البنوك المركزية والعوامل المؤسسية المؤثرة في الطلب على الذهب."),
    ("Weekly Markets Monitor", "World Gold Council", "تحليل كلي", "https://www.gold.org/goldhub/gold-focus/2026/11/weekly-markets-monitor-leveraged-repricers", "قراءة دورية للسياسة النقدية والتطورات الجيوسياسية والبيانات الاقتصادية المرتبطة بالذهب."),
    ("LBMA Snapshot Survey of Professional Analysts", "LBMA", "توقعات محللين", "https://www.lbma.org.uk/articles/gold-price-lbma-snapshot-survey-of-professional-analysts", "توقعات محللي المعادن المحترفين كما ينشرها المصدر، وليست توقعًا صادرًا عن GOLD-X."),
    ("Gold ETF Holdings and Flows", "World Gold Council", "صناديق ETF", "https://www.gold.org/goldhub/data/gold-etfs-holdings-and-flows", "تدفقات وحيازات صناديق الذهب المدعومة فعليًا، بحسب آخر تحديث منشور."),
]

OFFICIAL_SOURCES = [
    ("Federal Reserve / FOMC", "تقويم الاجتماعات والبيانات والمحاضر الرسمية للفيدرالي الأمريكي.", "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"),
    ("CME Group", "حجم التداول والفائدة المفتوحة لعقود الذهب والبيانات المرتبطة بها.", "https://www.cmegroup.com/markets/metals/precious/gold.volume.html"),
    ("CFTC COT", "تقرير التزامات المتداولين ومراكز الفئات المختلفة في العقود الآجلة.", "https://www.cftc.gov/dea/futures/deacmxsf.htm"),
    ("LBMA", "الأسعار المعيارية وبيانات المعادن الثمينة وتوقعات المحللين.", "https://www.lbma.org.uk/prices-and-data/lbma-precious-metal-prices"),
    ("CME FedWatch", "أداة متابعة توقعات السوق لاحتمالات قرارات الفائدة، وليست قرارًا رسميًا للفيدرالي.", "https://www.cmegroup.com/markets/interest-rates/cme-fedwatch-tool.html"),
]

LIVE_MARKET_LINKS = [
    ("Reuters Markets", "أخبار الأسواق العالمية والتحركات الاقتصادية اليومية.", "https://www.reuters.com/markets/"),
    ("CNBC Markets", "تغطية الأسواق والأسهم والعملات والسلع.", "https://www.cnbc.com/markets/"),
    ("World Gold Council", "أبحاث الذهب والطلب المؤسسي والتدفقات.", "https://www.gold.org/goldhub/research"),
]


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
    :root { --gold:#B7791F; --ink:#172033; --muted:#5B677A; --line:rgba(23,32,51,.12); --surface:#FFFFFF; --soft:#F5F7FB; }
    html, body, [class*="css"] { font-family:'IBM Plex Sans Arabic', sans-serif; }
    .stApp { background:linear-gradient(135deg,#F8FAFC 0%,#EEF3F8 58%,#FFF8E8 100%); color:var(--ink); }
    .block-container { max-width:1240px; padding-top:1.6rem; padding-bottom:3rem; }
    [data-testid="stHeader"] { background:rgba(248,250,252,.78); }
    [data-testid="stMetric"] { background:rgba(255,255,255,.86); border:1px solid var(--line); border-radius:16px; padding:1rem 1.15rem; box-shadow:0 10px 30px rgba(31,41,55,.07); }
    [data-testid="stMetricLabel"] { color:#5B677A; }
    [data-testid="stMetricValue"] { color:#172033; font-weight:700; }
    .hero { display:flex; justify-content:space-between; align-items:flex-end; gap:2rem; padding:1.4rem 0 1.1rem; border-bottom:1px solid var(--line); margin-bottom:1rem; }
    .eyebrow { color:var(--gold); font-size:.78rem; letter-spacing:.12em; text-transform:uppercase; font-weight:700; }
    .hero h1 { margin:.25rem 0 .35rem; color:#172033; font-size:clamp(2rem,4vw,3.4rem); line-height:1.12; letter-spacing:-.04em; }
    .hero p { color:var(--muted); margin:0; font-size:1.02rem; }
    .stamp { color:#42516A; font-size:.78rem; border:1px solid rgba(23,32,51,.16); border-radius:999px; padding:.5rem .8rem; white-space:nowrap; background:rgba(255,255,255,.62); }
    .section-kicker { display:flex; align-items:center; gap:.6rem; color:#172033; font-weight:700; font-size:1.05rem; margin:1.35rem 0 .75rem; }
    .section-kicker:before { content:''; width:8px; height:8px; border-radius:50%; background:var(--gold); box-shadow:0 0 12px rgba(183,121,31,.55); }
    .regime { display:inline-flex; align-items:center; gap:.5rem; border-radius:999px; padding:.5rem .9rem; margin-bottom:.4rem; font-weight:700; font-size:.95rem; }
    .regime-normal { color:#167044; background:#ECFDF3; border:1px solid #A7F3D0; }
    .regime-stress { color:#A34D00; background:#FFF7ED; border:1px solid #FED7AA; }
    .regime-crisis { color:#B42318; background:#FFF1F2; border:1px solid #FECDD3; }
    .radar-box,.gap-card,.growth-card { border-radius:16px; padding:1.1rem 1.25rem; background:rgba(255,255,255,.82); box-shadow:0 8px 24px rgba(31,41,55,.05); }
    .radar-critical { background:#FFF1F2; border:1px solid #FECDD3; }
    .radar-warning { background:#FFF7ED; border:1px solid #FED7AA; }
    .radar-clear { background:#ECFDF3; border:1px solid #A7F3D0; }
    .radar-title,.growth-card h3,.gap-card h3 { color:#172033; font-weight:700; }
    .radar-copy,.gap-card p,.growth-card p { color:#42516A; line-height:1.8; }
    .small-muted { color:#6B778C; font-size:.82rem; }
    .footnote { color:#6B778C; font-size:.78rem; border-top:1px solid var(--line); padding-top:1rem; margin-top:2rem; line-height:1.8; }
    div.stButton > button { border:1px solid rgba(183,121,31,.5); color:#6B4210; background:#FFF9EC; border-radius:10px; font-weight:600; }
    div.stButton > button:hover { border-color:var(--gold); color:#8B5E13; background:#FFF3D0; }
    button[data-baseweb="tab"] { font-weight:600; }
    .news-card { border:1px solid rgba(183,121,31,.2); border-right:4px solid var(--gold); border-radius:16px; padding:1rem 1.15rem; margin:.45rem 0; background:rgba(255,255,255,.88); box-shadow:0 8px 22px rgba(31,41,55,.05); }
    .news-card h3 { color:#172033; font-size:1.02rem; margin:.25rem 0 .4rem; }
    .news-card p { color:#42516A; line-height:1.75; margin:0; }
    .news-meta { color:#9A6416; font-size:.78rem; font-weight:700; }
    .source-card { border:1px solid rgba(23,32,51,.1); border-radius:14px; padding:.9rem 1rem; margin:.4rem 0; background:rgba(255,255,255,.7); }
    .source-card strong { color:#172033; }
    .source-card p { color:#5B677A; margin:.25rem 0 0; line-height:1.65; }
    .news-note { border-radius:14px; padding:.8rem 1rem; background:#FFF9EC; border:1px solid #F2D28A; color:#6B4210; line-height:1.7; }
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

main_tab, advanced_tab, sources_tab, news_center_tab = st.tabs(["📈 لوحة الذهب", "🧭 الطبقات المتقدمة", "🗂️ المصادر والحالة", "📰 الأخبار والتحليلات"])

with main_tab:

    # طبقة تعريفية مجانية: لا تتطلب تسجيل دخول ولا تجمع بيانات شخصية.
    st.markdown('<div class="section-kicker">عن المنصة</div>', unsafe_allow_html=True)
    intro_col, interest_col = st.columns([1.45, 1])
    with intro_col:
        st.markdown(
            """
            <div class="growth-card" dir="rtl">
              <h3>قراءة أوضح لسوق الذهب</h3>
              <p>استكشف السعر الحالي والتوقعات والعوامل المؤثرة مجاناً. GOLD-X أداة تحليلية تساعدك على فهم السيناريوهات، وليست وعداً بالربح أو بديلاً عن مستشار مالي مرخص.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with interest_col:
        st.markdown("**ما الذي يهمك أكثر؟**")
        interest = st.selectbox(
            "اختر اهتماماً واحداً (يُحفظ لهذه الجلسة فقط)",
            ["تحليل يومي للذهب", "العوامل الاقتصادية", "رادار المخاطر", "تعلم قراءة السوق"],
            label_visibility="collapsed",
        )
        st.caption(f"اختيارك الحالي: {interest}. لا يتم إرسال هذا الاختيار أو تخزينه خارج الجلسة.")

    @st.cache_data(ttl=300, show_spinner=False)
    def load_market_data():
        """يحد من الطلبات المتكررة مع إبقاء زر التحديث متاحاً للمستخدم."""
        return fetch_live_data()


    with st.spinner("جاري جلب البيانات الحية..."):
        raw_data = load_market_data()

    if raw_data is None:
        st.error("تعذر جلب سعر الذهب من المصدر الأساسي والاحتياطي. تحقق من الاتصال ثم أعد المحاولة لاحقاً.")
        st.stop()

    assert raw_data is not None
    quality = raw_data.get("data_quality", "unknown")
    quality_labels = {
        "live": "بيانات مباشرة من المصدر الأساسي",
        "partial": "بيانات جزئية: بعض المؤشرات تستخدم قيماً افتراضية",
        "fallback": "بيانات احتياطية: سعر الذهب من مصدر بديل",
        "cached": "آخر بيانات محفوظة محلياً: تعذر التحديث الحي مؤقتاً",
        "unknown": "حالة المصدر غير محددة",
    }
    if quality == "live":
        st.success(f"{quality_labels[quality]} · {raw_data.get('data_source', 'غير محدد')} · {raw_data.get('updated_at_utc', '')}")
    else:
        st.warning(f"{quality_labels.get(quality, quality)} · {raw_data.get('data_source', 'غير محدد')} · {raw_data.get('updated_at_utc', '')}")
    for data_warning in raw_data.get("data_warnings", []):
        st.caption(f"تنبيه مصدر البيانات: {data_warning}")

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

    st.markdown('<div class="section-kicker">🕰️ تقدير فجوة الافتتاح بعد الإجازة أو نهاية الأسبوع</div>', unsafe_allow_html=True)
    gap = result["opening_gap"]
    if gap["status"] == "INSUFFICIENT":
        st.warning(f"{gap['direction']}: {gap['message']}")
    else:
        gap_col1, gap_col2, gap_col3 = st.columns(3)
        with gap_col1:
            st.metric("الاتجاه الأرجح", gap["direction"])
        with gap_col2:
            st.metric("التغير المتوقع", f"{gap['expected_pct'] * 100:+.2f}%")
        with gap_col3:
            st.metric("احتمال الارتفاع", f"{gap['probability_up'] * 100:.0f}%")
        st.markdown(
            f'<div class="gap-card" dir="rtl"><h3>النطاق المحتمل عند الافتتاح: {gap["lower_pct"] * 100:+.2f}% إلى {gap["upper_pct"] * 100:+.2f}%</h3><p>{gap["message"]} درجة الثقة: {gap["confidence"]:.0f}/100.</p></div>',
            unsafe_allow_html=True,
        )

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
        font=dict(family="IBM Plex Sans Arabic", color="#42516A"),
        yaxis=dict(title="المساهمة النسبية (%)", gridcolor="rgba(23,32,51,.10)", zerolinecolor="rgba(183,121,31,.35)"),
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

    # تجهيز النشرة بدون تخزين البريد: الربط الفعلي يحتاج مزوداً خارجياً وموافقة المستخدم.
    st.markdown('<div class="section-kicker">📬 نشرة GOLD-X</div>', unsafe_allow_html=True)
    st.write("احصل مستقبلاً على ملخصات السوق الأسبوعية. هذا النموذج لا يرسل أو يحفظ البريد حالياً؛ أضف مزود نشرة بعد اختيار سياسة الخصوصية وموافقة المستخدم.")
    with st.form("newsletter_interest_form", clear_on_submit=True):
        email = st.text_input("البريد الإلكتروني (اختياري)", placeholder="name@example.com")
        consent = st.checkbox("أوافق على استخدام البريد للاشتراك في النشرة عند تفعيلها")
        submitted = st.form_submit_button("تسجيل الاهتمام")
    if submitted:
        if not consent:
            st.warning("يرجى تفعيل الموافقة أولاً. لم يتم حفظ أي بيانات.")
        elif not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email.strip()):
            st.warning("أدخل بريداً إلكترونياً صحيحاً. لم يتم حفظ أي بيانات.")
        else:
            st.success("تم تسجيل اهتمامك لهذه الجلسة فقط. لم يُحفظ البريد لأن خدمة النشرة لم تُربط بعد.")

    # تجهيز تجاري واضح دون ادعاء وجود دفع أو إعلانات فعلية.
    st.markdown('<div class="section-kicker">🚀 ما القادم؟</div>', unsafe_allow_html=True)
    free_col, premium_col, partner_col = st.columns(3)
    with free_col:
        st.markdown("<div class='growth-card' dir='rtl'><h3>الخطة المجانية</h3><p>بيانات السوق والتحليل الأساسي والتحديث عند الطلب متاحة للزوار دون تسجيل دخول.</p></div>", unsafe_allow_html=True)
    with premium_col:
        st.markdown("<div class='growth-card' dir='rtl'><h3>Premium قريباً</h3><p>قد تشمل تقارير دورية وتنبيهات وسجل أداء النموذج بعد إضافة حسابات ودفع آمن. لا توجد مدفوعات مفعّلة حالياً.</p></div>", unsafe_allow_html=True)
    with partner_col:
        st.markdown("<div class='growth-card' dir='rtl'><h3>رعاية وشراكات</h3><p>هذه مساحة مهيأة لرعاية أو رابط تابع بعد مراجعة الجهة والإفصاح عنه بوضوح. لا توجد إعلانات أو روابط تداول مفعّلة حالياً.</p></div>", unsafe_allow_html=True)

    st.markdown(
        '<div class="footnote">⚠️ هذا النموذج أداة مساعدة للتفكير، وليس نصيحة استثمارية. الأسواق متغيرة والنتائج التقديرية ليست ضماناً للأداء المستقبلي. لا يتم جمع بيانات شخصية أو حفظ البريد في هذه النسخة.</div></div>',
        unsafe_allow_html=True,
    )

with advanced_tab:
    st.markdown('<div class="section-kicker">طبقات GOLD-X المتقدمة</div>', unsafe_allow_html=True)
    st.info("هذه لوحة مستقلة للتجارب المتقدمة. لا تغيّر السعر المتوقع أو توصية النموذج الأساسي.")
    optional = fetch_optional_market_data()
    advanced_data = dict(raw_data)
    advanced_data.update(optional)
    snapshot = build_advanced_snapshot(advanced_data)
    a, b, c = st.columns(3)
    with a:
        st.metric("احتمال الركود التضخمي", f"{snapshot['stagflation_score']:.1f}%")
    with b:
        st.metric("خطر العدوى الرقمية", f"{snapshot['crypto_contagion_score']:.1f}%")
    with c:
        st.metric("ميل المحركات الهيكلية", f"{snapshot['structural_bias']:.1f}/100")
    st.markdown(f"**القراءة الحالية:** {advanced_summary(snapshot)}")
    st.markdown('<div class="section-kicker">المؤشرات الإضافية</div>', unsafe_allow_html=True)
    oil_label = f"{snapshot['oil_change_5d'] * 100:+.2f}%" if snapshot['oil_change_5d'] is not None else "غير متاح"
    btc_label = f"{snapshot['btc_change_5d'] * 100:+.2f}%" if snapshot['btc_change_5d'] is not None else "غير متاح"
    st.write(f"تغير النفط خلال 5 أيام: **{oil_label}** · تغير البيتكوين خلال 5 أيام: **{btc_label}**")
    for note in snapshot["notes"]:
        st.caption(f"• {note}")
    if st.button("🔄 تحديث الطبقات المتقدمة", key="refresh_advanced", use_container_width=True):
        st.rerun()

with sources_tab:
    st.markdown('<div class="section-kicker">مصادر البيانات وحالة النظام</div>', unsafe_allow_html=True)
    quality_text = quality_labels.get(raw_data.get("data_quality", "unknown"), raw_data.get("data_quality", "unknown"))
    if raw_data.get("storage_status") == "cached":
        st.warning(f"{quality_text} · {raw_data.get('storage_saved_at_utc', 'وقت الحفظ غير معروف')}")
    else:
        st.success(f"{quality_text} · {raw_data.get('data_source', 'غير محدد')}")
    st.write("التبويب الأساسي يحافظ على النموذج الحالي كما هو. التبويب المتقدم يعرض مؤشرات مستقلة ولا يحقن بيانات افتراضية في التوصية الأساسية.")
    st.caption(f"ملف البيانات المحلي: {raw_data.get('storage_file', 'data/market_data.json')}")
    st.markdown("**اختصارات الاستخدام**")
    st.markdown("""
    • استخدم تبويب **لوحة الذهب** للسعر والتوصية الحالية.
    • استخدم **الطبقات المتقدمة** لقراءة الركود التضخمي والعدوى الرقمية.
    • استخدم **المصادر والحالة** لمعرفة جودة البيانات قبل اتخاذ أي قرار.
    • زر التحديث في كل قسم يعيد جلب البيانات دون تغيير إعدادات النموذج.
    """)

with news_center_tab:
    st.markdown('<div class="section-kicker">مركز الأخبار والتحليلات المالية</div>', unsafe_allow_html=True)
    st.markdown('<div class="news-note">هذا المركز يعيد عرض روابط الجهات الأصلية التي كانت موجودة في الموقع. المقالات والتوقعات الخارجية للمطالعة فقط، ولا تمثل توصية من GOLD-X ولا تدخل تلقائيًا في معادلة السعر.</div>', unsafe_allow_html=True)
    articles_tab, rates_tab, experts_tab, official_tab = st.tabs(["مقالات الذهب", "الفائدة والفيدرالي", "الخبراء والبنوك", "المصادر الرسمية"])
    with articles_tab:
        st.caption("مواد أصلية من مجلس الذهب العالمي وLBMA حول الطلب والتدفقات والاتجاهات الكلية.")
        for title, organization, category, url, summary in NEWS_ITEMS:
            st.markdown(f'<div class="news-card" dir="rtl"><div class="news-meta">{organization} · {category}</div><h3>{title}</h3><p>{summary}</p></div>', unsafe_allow_html=True)
            st.link_button("فتح المقال الأصلي ↗", url, use_container_width=False)
    with rates_tab:
        st.markdown('<div class="news-card" dir="rtl"><div class="news-meta">Federal Reserve · FOMC</div><h3>اجتماعات وبيانات الفائدة الأمريكية</h3><p>تابع التقويم الرسمي للاجتماعات والبيانات والمحاضر. المصدر الرسمي لا يعرض توقعًا آليًا، بل القرار والوثائق المنشورة.</p></div>', unsafe_allow_html=True)
        st.link_button("فتح تقويم الفيدرالي ↗", "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm")
        st.markdown('<div class="news-card" dir="rtl"><div class="news-meta">CME FedWatch</div><h3>احتمالات قرارات الفائدة بحسب تسعير السوق</h3><p>أداة CME تعرض احتمالات السوق المسعّرة للعقود الآجلة. هي قراءة لتسعير السوق وليست إعلانًا من البنك الفيدرالي.</p></div>', unsafe_allow_html=True)
        st.link_button("فتح CME FedWatch ↗", "https://www.cmegroup.com/markets/interest-rates/cme-fedwatch-tool.html")
    with experts_tab:
        st.caption("التوقعات الخارجية تُعرض مع نسبتها إلى مصدرها، ولا يتم خلطها مع توقع GOLD-X الداخلي.")
        st.markdown('<div class="news-card" dir="rtl"><div class="news-meta">LBMA · Professional Analysts</div><h3>استطلاع توقعات محللي المعادن</h3><p>مقارنة آراء محللين محترفين حول الذهب والمعادن الثمينة من خلال المصدر الأصلي.</p></div>', unsafe_allow_html=True)
        st.link_button("فتح استطلاع LBMA ↗", "https://www.lbma.org.uk/articles/gold-price-lbma-snapshot-survey-of-professional-analysts")
        st.markdown('<div class="news-card" dir="rtl"><div class="news-meta">World Gold Council · Research</div><h3>أبحاث الطلب المؤسسي والتدفقات</h3><p>أبحاث مجلس الذهب العالمي حول البنوك المركزية وصناديق ETF واتجاهات الطلب العالمي.</p></div>', unsafe_allow_html=True)
        st.link_button("فتح أبحاث مجلس الذهب العالمي ↗", "https://www.gold.org/goldhub/research")
    with official_tab:
        for name, description, url in OFFICIAL_SOURCES:
            st.markdown(f'<div class="source-card" dir="rtl"><strong>{name}</strong><p>{description}</p></div>', unsafe_allow_html=True)
            st.link_button(f"فتح مصدر {name} ↗", url, use_container_width=False)
        st.markdown("**مراكز أخبار الأسواق**")
        for name, description, url in LIVE_MARKET_LINKS:
            st.markdown(f'<div class="source-card" dir="rtl"><strong>{name}</strong><p>{description}</p></div>', unsafe_allow_html=True)
            st.link_button(f"فتح {name} ↗", url, use_container_width=False)
