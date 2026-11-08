"""واجهة GOLD-X 2.0 بهوية ذهبية ومركز أخبار ومؤشرات رسمية."""
import json
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
from data_fetcher import fetch_live_data
from model import gold_x_model

GLOBAL = {"USD":"الدولار الأمريكي","EUR":"اليورو","GBP":"الجنيه الإسترليني","JPY":"الين الياباني","CNY":"اليوان الصيني","CHF":"الفرنك السويسري","CAD":"الدولار الكندي","AUD":"الدولار الأسترالي","INR":"الروبية الهندية","SGD":"الدولار السنغافوري"}
ARAB = {"AED":"الدرهم الإماراتي","BHD":"الدينار البحريني","DZD":"الدينار الجزائري","DJF":"الفرنك الجيبوتي","EGP":"الجنيه المصري","IQD":"الدينار العراقي","JOD":"الدينار الأردني","KWD":"الدينار الكويتي","LBP":"الليرة اللبنانية","LYD":"الدينار الليبي","MAD":"الدرهم المغربي","MRU":"الأوقية الموريتانية","OMR":"الريال العُماني","QAR":"الريال القطري","SAR":"الريال السعودي","SDG":"الجنيه السوداني","SOS":"الشلن الصومالي","SYP":"الليرة السورية","TND":"الدينار التونسي","YER":"الريال اليمني","KMF":"الفرنك القمري","ILS":"الشيكل المستخدم في فلسطين"}
NAMES = {**GLOBAL, **ARAB}
SYMBOLS = {"USD":"$","EUR":"€","GBP":"£","JPY":"¥","CNY":"¥","CHF":"CHF","CAD":"C$","AUD":"A$","INR":"₹","SGD":"S$","AED":"د.إ","BHD":"د.ب","DZD":"دج","DJF":"Fdj","EGP":"ج.م","IQD":"ع.د","JOD":"د.أ","KWD":"د.ك","LBP":"ل.ل","LYD":"ل.د","MAD":"د.م","MRU":"أوقية","OMR":"ر.ع","QAR":"ر.ق","SAR":"ر.س","SDG":"ج.س","SOS":"ش.ص","SYP":"ل.س","TND":"د.ت","YER":"ر.ي","KMF":"KMF","ILS":"₪"}
NEWS = [
("إحصاءات مشتريات البنوك المركزية — سبتمبر 2026","World Gold Council","طلب مؤسسي","https://www.gold.org/goldhub/gold-focus/2026/11/central-bank-gold-statistics-september-2026","متابعة مشتريات البنوك المركزية والعوامل المؤسسية المؤثرة في الطلب على الذهب."),
("Weekly Markets Monitor — Leveraged repricers","World Gold Council","تحليل كلي","https://www.gold.org/goldhub/gold-focus/2026/11/weekly-markets-monitor-leveraged-repricers","قراءة أسبوعية للسياسة النقدية والتطورات الجيوسياسية والبيانات الاقتصادية المرتبطة بالذهب."),
("LBMA Snapshot Survey of Professional Analysts","LBMA","توقعات محللين","https://www.lbma.org.uk/articles/gold-price-lbma-snapshot-survey-of-professional-analysts","متوسط توقعات محللي المعادن المحترفين كما ينشره المصدر، وليس توقع GOLD-X."),
("Gold ETF Holdings and Flows","World Gold Council","صناديق ETF","https://www.gold.org/goldhub/data/gold-etfs-holdings-and-flows","تدفقات وحيازات صناديق الذهب المدعومة فعلياً، محدثة أسبوعياً وشهرياً."),
]
SOURCES = [("CFTC COT","مراكز المتداولين في عقود الذهب","https://www.cftc.gov/dea/futures/deacmxsf.htm"),("CME","حجم التداول والفائدة المفتوحة","https://www.cmegroup.com/markets/metals/precious/gold.volume.html"),("Federal Reserve","تقويم اجتماعات FOMC والبيانات والمحاضر","https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"),("LBMA","السعر المعياري وبيانات المعادن الثمينة","https://www.lbma.org.uk/prices-and-data/lbma-precious-metal-prices")]

st.set_page_config(page_title="GOLD-X 2.0 | فخامة الذهب", page_icon="🥇", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Arabic:wght@400;500;600;700&display=swap');
:root{--gold:#F1C75B;--cream:#FFF7D6;--line:rgba(241,199,91,.3)}
html,body,[class*="css"]{font-family:'IBM Plex Sans Arabic',sans-serif}.stApp{color:#F8FAFC;background:radial-gradient(circle at 82% -8%,rgba(241,199,91,.23),transparent 31%),radial-gradient(circle at 7% 40%,rgba(40,75,125,.18),transparent 26%),#070A10}.block-container{max-width:1240px;padding-top:2.2rem;padding-bottom:3rem}[data-testid="stHeader"]{background:transparent}[data-testid="stMetric"]{background:linear-gradient(145deg,rgba(25,34,50,.98),rgba(10,15,25,.96));border:1px solid var(--line);border-radius:18px;padding:1rem;box-shadow:0 18px 55px rgba(0,0,0,.25)}[data-testid="stMetricLabel"]{color:#D4DCE8}[data-testid="stMetricValue"]{color:#FFF;font-weight:700}.hero{display:flex;justify-content:space-between;align-items:flex-end;gap:2rem;padding:1.8rem 0 1.35rem;border-bottom:1px solid rgba(148,163,184,.16);margin-bottom:1.3rem}.eyebrow{color:var(--gold);font-size:.78rem;letter-spacing:.12em;font-weight:700}.hero h1{margin:.25rem 0 .35rem;font-size:clamp(2.1rem,4vw,3.7rem);line-height:1.1;background:linear-gradient(110deg,#FFF7D6,#F1C75B,#9C6816);-webkit-background-clip:text;background-clip:text;color:transparent}.hero p{color:#D4DCE8;margin:0;font-size:1.03rem}.stamp{color:#FFF7D6;font-size:.78rem;border:1px solid var(--line);border-radius:999px;padding:.5rem .8rem;white-space:nowrap}.section-kicker{display:flex;align-items:center;gap:.6rem;color:var(--cream);font-weight:700;font-size:1.1rem;margin:1.6rem 0 .75rem}.section-kicker:before{content:'';width:8px;height:8px;border-radius:50%;background:var(--gold);box-shadow:0 0 15px var(--gold)}.card{border:1px solid rgba(241,199,91,.25);border-right:4px solid var(--gold);border-radius:16px;padding:1rem 1.1rem;margin:.5rem 0;background:linear-gradient(135deg,rgba(25,34,50,.98),rgba(12,17,28,.98))}.card h4{color:var(--cream);margin:0 0 .35rem}.card p{color:#D4DCE8;margin:0;line-height:1.75}.meta{color:var(--gold);font-size:.8rem;font-weight:700}.footnote{color:#AAB7C9;font-size:.8rem;border-top:1px solid rgba(148,163,184,.16);padding-top:1rem;margin-top:2rem;line-height:1.8}[data-testid="stWidgetLabel"] p,[data-testid="stCaptionContainer"] p{color:#D4DCE8!important}div[data-baseweb="select"]>div{background:#151D2B;border-color:var(--line);color:#FFF}div.stButton>button,a[role="button"]{border:1px solid rgba(241,199,91,.55);color:var(--cream)!important;background:linear-gradient(135deg,rgba(241,199,91,.16),rgba(241,199,91,.04));border-radius:12px;font-weight:600}
</style><div dir="rtl">""", unsafe_allow_html=True)
st.markdown('<div class="hero" dir="rtl"><div><div class="eyebrow">GOLD-X / MARKET INTELLIGENCE</div><h1>🥇 GOLD-X 2.0</h1><p>منصة فاخرة لقراءة سوق الذهب: السعر، المؤشرات، الأخبار، والسيناريوهات</p></div><div class="stamp">تحديث عند الطلب · بيانات موثقة</div></div>', unsafe_allow_html=True)

@st.cache_data(ttl=300, show_spinner=False)
def market(): return fetch_live_data()
@st.cache_data(ttl=1800, show_spinner=False)
def fx_rates():
    try:
        r=requests.get("https://open.er-api.com/v6/latest/USD",timeout=8); r.raise_for_status(); rates=r.json().get("rates",{}); rates["USD"]=1.0
        return {c:float(rates[c]) for c in NAMES if c in rates}
    except Exception: return {"USD":1.0}

with st.spinner("جاري تجهيز لوحة الذهب..."): raw=market()
if raw is None: st.error("تعذر جلب بيانات الذهب حالياً. أعد المحاولة بعد قليل."); st.stop()
quality=raw.get("data_quality","unknown"); source=raw.get("data_source","غير محدد")
(st.success if quality=="live" else st.warning)(f"مصدر البيانات: {source} · الحالة: {quality} · {raw.get('updated_at_utc','')}")
result=gold_x_model(raw)
cols=st.columns(3)
with cols[0]: st.metric("الأونصة الحالية",f"${raw['current_price']:,.0f}",delta=f"{raw['price_change']*100:+.2f}%")
with cols[1]: st.metric("السعر المتوقع",f"${result['predicted_price']:,.0f}",delta=f"{result['change_pct']*100:+.2f}%")
with cols[2]: st.metric("درجة الثقة",f"{result['confidence']:.1f}/10")

st.markdown('<div class="section-kicker">💱 تحويل أسعار الذهب</div>',unsafe_allow_html=True)
options=list(GLOBAL)+[c for c in ARAB if c not in GLOBAL]
cc,nc=st.columns([1,2])
with cc: selected=st.selectbox("اختر العملة",options,format_func=lambda c:f"{c} — {NAMES[c]}",key="currency")
selected=str(selected); rates=fx_rates(); rate=float(rates.get(selected,1.0))
with nc: st.caption(f"1 USD = {rate:,.4g} {selected} · يتم تحديث سعر الصرف كل 30 دقيقة")
ounce=float(raw["current_price"]); g24=ounce/31.1034768; prices={"الأونصة":ounce,"جرام 24":g24,"جرام 21":g24*21/24,"جرام 18":g24*18/24,"الجنيه 21 / 8g":g24*21/24*8}
for col,(label,value) in zip(st.columns(5),prices.items()):
    with col: st.metric(label,f"{SYMBOLS.get(selected,selected)} {value*rate:,.2f}")
st.caption("القيم نظرية للذهب الخام ولا تشمل المصنعية أو الضريبة أو هامش التاجر. الجنيه محسوب بوزن 8 جرام من عيار 21.")

st.markdown('<div class="section-kicker">📰 مركز الأخبار والمؤشرات العالمية</div>',unsafe_allow_html=True)
news_tab,indicator_tab,source_tab=st.tabs(["أهم المقالات والتحليلات","مؤشرات السوق","المصادر الرسمية"])
with news_tab:
    st.caption("روابط أصلية إلى أحدث مواد الجهات المتخصصة، ولا تمثل توصية من GOLD-X.")
    for title,org,tag,url,summary in NEWS:
        st.markdown(f'<div class="card" dir="rtl"><div class="meta">{org} · {tag}</div><h4>{title}</h4><p>{summary}</p></div>',unsafe_allow_html=True); st.link_button("فتح المقال الأصلي ↗",url)
with indicator_tab:
    ic=st.columns(5); values=[("DXY",raw.get("dxy_change",0)*100,"% / 5 أيام"),("NASDAQ",raw.get("sp500_change_5d",0)*100,"% / 5 أيام"),("VIX",raw.get("vix",20),"تقلب"),("ارتباط ذهب/أسهم",raw.get("gold_equity_corr",0),"معامل"),("الحجم",raw.get("volume_spike",1),"نسبي")]
    for col,(label,value,note) in zip(ic,values):
        with col: st.metric(label,f"{value:.2f}"); st.caption(note)
    st.info("هذه المؤشرات تساعد على قراءة البيئة المحيطة بالذهب. القيم الافتراضية تُعلن في حالة جودة البيانات أعلى الصفحة.")
with source_tab:
    for name,description,url in SOURCES:
        with st.container(): st.markdown(f'<div class="card" dir="rtl"><div class="meta">{name}</div><p>{description}</p></div>',unsafe_allow_html=True); st.link_button(f"فتح مصدر {name} ↗",url)

regime={"NORMAL":("🟢","طبيعي"),"STRESS":("🟠","متوتر"),"CRISIS":("🔴","أزمة")}; icon,label=regime.get(result["regime"],("⚪","غير محدد"))
st.markdown(f'<div class="section-kicker">قراءة الحالة</div><div class="card"><h4>{icon} السوق {label}</h4><p>{result["recommendation"]}</p></div>',unsafe_allow_html=True)
radar=result["radar"]; st.markdown(f'<div class="section-kicker">📡 رادار البيع القسري</div><div class="card"><div class="meta">{radar["status"]} · {radar["score"]}/10</div><p>{radar["msg"]}</p></div>',unsafe_allow_html=True)
if result["warnings"]:
    for warning in result["warnings"]: st.warning(warning)
chart=pd.DataFrame({"العامل":["اقتصادي","تدفقات","ذكاء اصطناعي"],"القيمة":[result["breakdown"]["economic"]*100,result["breakdown"]["flow"]*100,result["breakdown"]["ai"]*100]})
fig=go.Figure(go.Bar(x=chart["العامل"],y=chart["القيمة"],marker_color=["#D8A72C","#F1C75B","#8CA8D8"],text=[f"{x:+.2f}%" for x in chart["القيمة"]],textposition="outside")); fig.update_layout(height=300,paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",font={"color":"#D4DCE8","family":"IBM Plex Sans Arabic"},showlegend=False); st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False})
with st.expander("📊 البيانات الخام المستخدمة"): st.json(json.loads(json.dumps(raw,default=float)))
if st.button("🔄 تحديث البيانات",use_container_width=False): market.clear(); fx_rates.clear(); st.rerun()
st.markdown('<div class="footnote">⚠️ GOLD-X أداة تحليلية وليست نصيحة استثمارية. تحقق من المصادر الأصلية قبل أي قرار مالي.</div></div>',unsafe_allow_html=True)
