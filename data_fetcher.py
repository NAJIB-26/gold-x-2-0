"""موصل بيانات GOLD-X 2.0 متعدد المصادر مع فشل جزئي آمن."""

import io
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional, cast

import numpy as np
import pandas as pd
import requests
try:
    import yfinance as yf  # type: ignore[reportMissingImports]
except Exception:  # يسمح بتشغيل المصدر الاحتياطي حتى عند تعذر تثبيت Yahoo.
    yf = None


# العوامل التي لا تتوفر مباشرة عبر المصدر المجاني وتُحدّث يدوياً عند الحاجة.
MANUAL_DEFAULTS = {
    "tip_change": 0.002,
    "cpi_change": 0.004,
    "fed_stance": -0.5,
    "algo_intensity": 0.75,
    "open_interest_ratio": 1.5,
    "etf_outflow_ratio": 0.01,
    "ai_bubble_score": 0.7,
    "ai_earnings_surprise": 0.0,
    "ipo_sentiment": 0.0,
}

TICKERS = {
    "gold": "GC=F",
    "dxy": "DX-Y.NYB",
    "nasdaq": "^IXIC",
    "vix": "^VIX",
}

# بدائل يومية عامة من FRED للمؤشرات الثانوية. DTWEXBGS هو مؤشر الدولار
# الواسع وليس DXY نفسه، لذلك نعرض مصدره بوضوح ولا نقدمه كبديل مطابق.
FRED_SERIES = {
    "dxy": "DTWEXBGS",
    "nasdaq": "NASDAQCOM",
    "vix": "VIXCLS",
}


def _history(ticker: str, period: str = "1mo") -> Any:
    """تحميل سجل صغير بمحاولة واحدة حتى لا يعلق تشغيل Streamlit."""
    if yf is None:
        raise RuntimeError("مكتبة Yahoo Finance غير متاحة")
    try:
        frame = yf.download(
            ticker,
            period=period,
            auto_adjust=False,
            progress=False,
            threads=False,
            timeout=5,
        )
        if frame is None or frame.empty:
            raise ValueError(f"لم تصل بيانات للرمز {ticker}")
        if isinstance(frame.columns, pd.MultiIndex):
            frame.columns = frame.columns.get_level_values(0)
        cleaned = frame.dropna(how="all")
        if cleaned.empty:
            raise ValueError(f"السجل فارغ للرمز {ticker}")
        return cleaned
    except Exception as exc:  # قد يحدث تقييد أو انقطاع مؤقت.
        raise ValueError(f"فشل جلب {ticker}: {exc}") from exc


def _close_series(ticker: str, period: str = "1mo") -> pd.Series:
    frame = _history(ticker, period)
    series = cast(pd.Series, frame["Close"].dropna())
    if series.empty:
        raise ValueError(f"لا توجد أسعار إغلاق صالحة للرمز {ticker}")
    return series


def _fred_series(series_id: str, period: str = "1mo") -> pd.Series:
    """تحميل سلسلة FRED العامة بصيغة CSV دون الحاجة إلى مفتاح API."""
    response = requests.get(
        f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}",
        params={"cosd": "2026-01-01"},
        timeout=8,
    )
    response.raise_for_status()
    frame = pd.read_csv(io.StringIO(response.text))
    if frame.shape[1] < 2:
        raise ValueError(f"لم تصل سلسلة FRED {series_id}")
    series = pd.to_numeric(frame.iloc[:, 1], errors="coerce").dropna()
    if series.empty:
        raise ValueError(f"سلسلة FRED {series_id} فارغة")
    return series.tail(32).reset_index(drop=True)


def _metals_api_key() -> str:
    """قراءة المفتاح اختيارياً من البيئة أو Streamlit Secrets دون طباعته."""
    key = os.getenv("METALS_API_KEY", "").strip()
    if key:
        return key
    try:
        import streamlit as st  # type: ignore[reportMissingImports]

        return str(st.secrets.get("METALS_API_KEY", "")).strip()
    except Exception:
        return ""


def _metals_api_gold() -> Optional[float]:
    """محاولة جلب XAU/USD من Metals-API عند توفر مفتاح اختياري."""
    key = _metals_api_key()
    if not key:
        return None
    response = requests.get(
        "https://metals-api.com/api/latest",
        params={"access_key": key, "base": "USD", "symbols": "XAU"},
        timeout=8,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("success") is False:
        raise ValueError(str(payload.get("error", "Metals-API rejected the request")))
    rates = payload.get("rates", {})
    direct = rates.get("USDXAU")
    if direct is not None:
        return float(direct)
    inverse = rates.get("XAU")
    if inverse:
        return float(1 / float(inverse))
    return None


def _public_gold_api() -> Optional[float]:
    """مصدر عام لسعر XAU/USD لا يحتاج مفتاحاً؛ يستخدم كحل احتياطي أخير."""
    response = requests.get("https://api.gold-api.com/price/XAU/USD", timeout=8)
    response.raise_for_status()
    payload = response.json()
    price = payload.get("price")
    if price is None or float(price) <= 0:
        raise ValueError("لم يُرجع Gold-API سعراً صالحاً")
    return float(price)


def _goldprice_dev_gold() -> Optional[float]:
    """مصدر احتياطي مجاني لسعر XAU/USD، لا يحتاج مفتاحاً في endpoint العام."""
    response = requests.get(
        "https://api.goldprice.dev/v1/prices",
        params={"symbol": "XAU-USD-SPOT"},
        timeout=6,
    )
    response.raise_for_status()
    symbols = response.json().get("symbols", [])
    if not symbols:
        raise ValueError("لم يُرجع goldprice.dev رموزاً")
    price = float(symbols[0].get("price", 0))
    if price <= 0:
        raise ValueError("لم يُرجع goldprice.dev سعراً صالحاً")
    return price


def _series_change(series: Optional[pd.Series], periods: int = 5) -> Optional[float]:
    if series is None or len(series) <= periods:
        return None
    values = series.pct_change(periods).dropna()
    return float(values.iloc[-1]) if not values.empty else None


def _latest(series: Optional[pd.Series]) -> Optional[float]:
    if series is None or series.empty:
        return None
    return float(series.iloc[-1])


def fetch_live_data() -> Optional[Dict[str, Any]]:
    """إرجاع البيانات مع مصدر وحالة جودة، دون إسقاط الموقع عند فشل مؤشر ثانوي."""
    warnings = []
    series: Dict[str, Optional[pd.Series]] = {}
    source_by_name: Dict[str, str] = {}

    for name, ticker in TICKERS.items():
        try:
            series[name] = _close_series(ticker, "1mo")
            source_by_name[name] = "Yahoo Finance"
        except Exception as exc:
            series[name] = None
            fred_id = FRED_SERIES.get(name)
            if fred_id:
                try:
                    series[name] = _fred_series(fred_id)
                    source_by_name[name] = f"FRED/{fred_id}"
                    warnings.append(f"تم استخدام FRED/{fred_id} كبديل يومي لـ {name}.")
                    continue
                except Exception as fred_exc:
                    warnings.append(f"تعذر تحديث {name} من Yahoo وFRED: {fred_exc}")
            else:
                if name != "gold":
                    warnings.append(f"تعذر تحديث {name}: {exc}")

    gold_close = series["gold"]
    metals_gold: Optional[float] = None
    public_gold: Optional[float] = None
    if gold_close is None:
        try:
            metals_gold = _metals_api_gold()
        except Exception as exc:
            warnings.append(f"تعذر استخدام Metals-API الاحتياطي: {exc}")
        if metals_gold is None:
            try:
                public_gold = _goldprice_dev_gold()
            except Exception as exc:
                warnings.append(f"تعذر استخدام goldprice.dev الاحتياطي: {exc}")
                try:
                    public_gold = _public_gold_api()
                except Exception as public_exc:
                    warnings.append(f"تعذر استخدام Gold-API العام: {public_exc}")

    current_price = _latest(gold_close) or metals_gold or public_gold
    if current_price is None:
        print("GOLD-X data fetch failed: no gold source available")
        return None
    if gold_close is None:
        warnings.append("تعذر مصدر الذهب الأساسي؛ تم استخدام سعر الذهب الاحتياطي بنجاح.")

    observed_price_change = _series_change(gold_close, 1)
    price_change = observed_price_change or 0.0
    gold_change_5d = _series_change(gold_close, 5)
    gold_change_20d = _series_change(gold_close, 20)
    if gold_close is not None and len(gold_close) >= 6:
        gold_returns = gold_close.pct_change().dropna()
        gold_volatility_10d = float(gold_returns.tail(10).std()) if len(gold_returns) >= 3 else 0.006
    else:
        gold_volatility_10d = None
    dxy_change = _series_change(series["dxy"], 5)
    nasdaq_change = _series_change(series["nasdaq"], 5)
    vix_value = _latest(series["vix"])

    gold_values = gold_close.pct_change().dropna().to_numpy(dtype=float) if gold_close is not None else np.array([])
    nasdaq = series["nasdaq"]
    equity_values = nasdaq.pct_change().dropna().to_numpy(dtype=float) if nasdaq is not None else np.array([])
    paired = min(len(gold_values), len(equity_values))
    if paired >= 5:
        gold_equity_corr = float(np.corrcoef(gold_values[-paired:], equity_values[-paired:])[0, 1])
        if not np.isfinite(gold_equity_corr):
            gold_equity_corr = 0.0
    else:
        gold_equity_corr = 0.0

    available_secondary = sum(value is not None for value in (dxy_change, nasdaq_change, vix_value))
    secondary_sources = {source_by_name.get(name) for name in ("dxy", "nasdaq", "vix") if source_by_name.get(name)}
    if gold_close is not None and available_secondary == 3 and secondary_sources == {"Yahoo Finance"}:
        quality = "live"
        source = "Yahoo Finance"
    elif gold_close is not None:
        quality = "partial"
        source = "Yahoo Finance + " + "+".join(sorted(secondary_sources or {"defaults"}))
        if available_secondary < 3:
            warnings.append("بيانات الذهب متاحة، لكن بعض المؤشرات الثانوية تستخدم قيماً افتراضية.")
    else:
        quality = "fallback"
        if metals_gold is not None:
            gold_source = "Metals-API"
        elif public_gold is not None:
            gold_source = "goldprice.dev أو Gold-API"
        else:
            gold_source = "Gold-API"
        source = gold_source + (" + " + "+".join(sorted(secondary_sources)) if secondary_sources else " + defaults")
        if available_secondary < 3:
            warnings.append("يُعرض سعر الذهب من مصدر احتياطي مع مؤشرات ثانوية افتراضية.")

    result: Dict[str, Any] = {
        "current_price": current_price,
        "price_change": price_change,
        "gold_change_1d": observed_price_change,
        "gold_change_5d": gold_change_5d,
        "gold_change_20d": gold_change_20d,
        "gold_volatility_10d": gold_volatility_10d,
        "gold_history_available": gold_close is not None and len(gold_close) >= 6,
        "volume_spike": 1.0,
        "dxy_change": dxy_change if dxy_change is not None else 0.0,
        "sp500_change_5d": nasdaq_change if nasdaq_change is not None else 0.0,
        "vix": vix_value if vix_value is not None else 20.0,
        "gold_equity_corr": gold_equity_corr,
        "gold_ai_correlation": gold_equity_corr,
        **MANUAL_DEFAULTS,
        "data_source": source,
        "data_quality": quality,
        "data_warnings": warnings,
        "updated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }
    return result
