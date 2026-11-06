"""جلب بيانات السوق اللازمة لنموذج GOLD-X 2.0."""

from typing import Any, Dict, Optional, cast

import numpy as np
import pandas as pd
import yfinance as yf  # type: ignore[reportMissingImports]


# قيم العوامل التي لا تتوفر مباشرة عبر Yahoo Finance وتُحدّث يدوياً عند الحاجة.
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


def _history(ticker: str, period: str = "3mo") -> Any:
    """تحميل سجل سعر نظيف مع تعطيل الرسائل غير الضرورية من yfinance."""
    frame = yf.download(
        ticker,
        period=period,
        auto_adjust=False,
        progress=False,
        threads=False,
        timeout=12,
    )
    if frame is None or frame.empty:
        raise ValueError(f"لم تصل بيانات من Yahoo Finance للرمز {ticker}")
    if isinstance(frame.columns, pd.MultiIndex):
        frame.columns = frame.columns.get_level_values(0)
    return frame.dropna(how="all")


def _close_series(ticker: str, period: str = "3mo") -> pd.Series:
    frame = _history(ticker, period)
    series = cast(pd.Series, frame["Close"].dropna())
    if series.empty:
        raise ValueError(f"لا توجد أسعار إغلاق صالحة للرمز {ticker}")
    return series


def fetch_live_data() -> Optional[Dict[str, Any]]:
    """إرجاع البيانات الحية المطلوبة، أو None عند فشل مزود البيانات."""
    try:
        gold = _history("GC=F", "3mo")
        gold_close = cast(pd.Series, gold["Close"].dropna())
        if len(gold_close) < 10:
            raise ValueError("سجل الذهب قصير جداً لإجراء الحسابات")

        current_price = float(gold_close.iloc[-1])
        price_change = float(gold_close.pct_change().iloc[-1])
        recent_volume = cast(pd.Series, gold["Volume"].replace(0, np.nan).dropna())
        if recent_volume.empty:
            volume_spike = 1.0
        else:
            baseline = float(recent_volume.tail(20).mean()) or 1.0
            volume_spike = float(recent_volume.iloc[-1] / baseline)

        dxy = _close_series("DX-Y.NYB")
        # الحقل يحمل الاسم التاريخي sp500_change_5d في مواصفات GOLD-X،
        # لكن المصدر المطلوب هو ناسداك المركب ^IXIC كما هو محدد في الطلب.
        nasdaq = _close_series("^IXIC")
        vix = _close_series("^VIX", "1mo")

        dxy_change = float(dxy.pct_change(5).dropna().iloc[-1])
        sp500_change_5d = float(nasdaq.pct_change(5).dropna().iloc[-1])
        vix_value = float(vix.iloc[-1])

        joined = pd.concat(
            [gold_close.pct_change().rename("gold"), nasdaq.pct_change().rename("equity")],
            axis=1,
        ).dropna()
        gold_values = np.asarray(joined["gold"], dtype=float)
        equity_values = np.asarray(joined["equity"], dtype=float)
        gold_equity_corr = (
            float(np.corrcoef(gold_values, equity_values)[0, 1]) if len(joined) >= 5 else 0.0
        )
        if not np.isfinite(gold_equity_corr):
            gold_equity_corr = 0.0

        result: Dict[str, Any] = {
            "current_price": current_price,
            "price_change": price_change,
            "volume_spike": max(0.0, volume_spike),
            "dxy_change": dxy_change,
            "sp500_change_5d": sp500_change_5d,
            "vix": vix_value,
            "gold_equity_corr": gold_equity_corr,
            **MANUAL_DEFAULTS,
        }
        result["gold_ai_correlation"] = gold_equity_corr
        return result
    except Exception as exc:  # yfinance قد يفشل بسبب الشبكة أو حدود المزود.
        print(f"GOLD-X data fetch failed: {exc}")
        return None
