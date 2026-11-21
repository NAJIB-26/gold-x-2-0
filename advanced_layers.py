"""طبقات GOLD-X المتقدمة بشكل مستقل عن النموذج الأساسي.

هذه الوحدة لا تعدّل gold_x_model؛ تعرض مؤشرات إضافية تعليمية مع وسم واضح
للمصدر والحالة عندما تكون البيانات الحية غير متاحة.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

try:
    import yfinance as yf  # type: ignore[reportMissingImports]
except Exception:
    yf = None


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, float(value)))


def fetch_optional_market_data() -> Dict[str, Optional[float]]:
    """يجلب مؤشرات إضافية دون أن يمنعها فشلها من تشغيل الموقع."""
    result: Dict[str, Optional[float]] = {"oil_change_5d": None, "btc_change_5d": None}
    if yf is None:
        return result
    for key, ticker in (("oil_change_5d", "BZ=F"), ("btc_change_5d", "BTC-USD")):
        try:
            frame = yf.download(ticker, period="1mo", auto_adjust=False, progress=False, threads=False, timeout=5)
            if frame is None or frame.empty:
                continue
            close = frame["Close"]
            if hasattr(close, "columns"):
                close = close.iloc[:, 0]
            close = close.dropna()
            if len(close) > 5:
                result[key] = float(close.iloc[-1] / close.iloc[-6] - 1)
        except Exception:
            continue
    return result


def build_advanced_snapshot(data: Dict[str, Any]) -> Dict[str, Any]:
    """يبني لوحة متقدمة من البيانات المتاحة مع عدم اختلاق بيانات حية."""
    quality = str(data.get("data_quality", "unknown"))
    dxy = float(data.get("dxy_change", 0.0) or 0.0)
    oil_change = data.get("oil_change_5d")
    btc_change = data.get("btc_change_5d")
    vix = float(data.get("vix", 20.0) or 20.0)
    cpi = float(data.get("cpi_change", 0.004) or 0.0)
    fed = float(data.get("fed_stance", -0.5) or 0.0)

    oil_value = float(oil_change) if oil_change is not None else 0.0
    btc_value = float(btc_change) if btc_change is not None else 0.0
    stagflation_score = _clamp(
        50 + cpi * 1800 + oil_value * 220 - fed * 8 + max(vix - 20, 0) * 1.2,
        0,
        100,
    )
    crypto_contagion = _clamp(
        max(0, -btc_value) * 700 + max(vix - 22, 0) * 2.0,
        0,
        100,
    )
    structural_bias = _clamp(50 - dxy * 350 + (10 if quality == "live" else 0), 0, 100)

    return {
        "source_state": "مباشر" if quality == "live" else "جزئي / افتراضي",
        "stagflation_score": round(stagflation_score, 1),
        "crypto_contagion_score": round(crypto_contagion, 1),
        "structural_bias": round(structural_bias, 1),
        "oil_change_5d": oil_change,
        "btc_change_5d": btc_change,
        "notes": [
            "هذه الطبقة مستقلة عن السعر المتوقع الأساسي ولا تغيّر توصيته.",
            "العوامل غير المتاحة حيًا تظهر كقيم افتراضية أو غير متاحة بوضوح.",
            "لا تُعرض مشتريات البنوك المركزية أو الصناديق السيادية كبيانات حية دون مصدر موثوق.",
        ],
    }


def advanced_summary(snapshot: Dict[str, Any]) -> str:
    score = snapshot["stagflation_score"]
    if score >= 70:
        return "احتمال مرتفع نسبيًا لبيئة ركود تضخمي؛ راقب التضخم والطاقة والعوائد الحقيقية."
    if score >= 45:
        return "إشارات مختلطة؛ لا توجد قراءة حاسمة للركود التضخمي من البيانات المتاحة."
    return "احتمال منخفض نسبيًا وفق المدخلات الحالية، مع بقاء المؤشرات قابلة للتغير."
