"""نموذج GOLD-X 2.0 لتقدير اتجاه الذهب عبر طبقات اقتصادية وتدفقات وذكاء اصطناعي."""

from enum import Enum
from typing import Any, Dict


class MarketRegime(str, Enum):
    """حالة السوق المستخدمة لتغيير حساسية النموذج."""

    NORMAL = "NORMAL"
    STRESS = "STRESS"
    CRISIS = "CRISIS"


def detect_regime(
    vix: float,
    sp500_change_5d: float,
    gold_equity_corr: float,
    algo_intensity: float,
    open_interest_ratio: float,
) -> MarketRegime:
    """يحسب درجة ضغط السوق ثم يحدد حالته."""
    score = 0
    if vix > 35:
        score += 3
    elif vix > 25:
        score += 2
    elif vix > 20:
        score += 1

    if sp500_change_5d < -0.05:
        score += 3
    elif sp500_change_5d < -0.02:
        score += 2
    elif sp500_change_5d < 0:
        score += 1

    if gold_equity_corr > 0.4:
        score += 3
    elif gold_equity_corr > 0.2:
        score += 2

    if algo_intensity > 0.75:
        score += 2
    elif algo_intensity > 0.6:
        score += 1

    if open_interest_ratio > 1.8:
        score += 3
    elif open_interest_ratio > 1.4:
        score += 2

    if score >= 8:
        return MarketRegime.CRISIS
    if score >= 4:
        return MarketRegime.STRESS
    return MarketRegime.NORMAL


def economic_model(
    dxy_change: float,
    tip_change: float,
    cpi_change: float,
    fed_stance: float,
    regime: MarketRegime,
) -> float:
    """طبقة المؤشرات الاقتصادية؛ التغيرات كلها نسب عشرية."""
    betas = {
        MarketRegime.NORMAL: (-0.85, -1.20, 0.55, 0.20),
        MarketRegime.STRESS: (-0.60, -0.90, 0.70, 0.15),
        MarketRegime.CRISIS: (-0.30, -0.40, 0.30, 0.05),
    }
    beta_dxy, beta_tip, beta_cpi, beta_fed = betas[regime]
    return (
        beta_dxy * dxy_change
        + beta_tip * tip_change
        + beta_cpi * cpi_change
        + beta_fed * fed_stance
    )


def flow_model(
    open_interest_ratio: float,
    volume_spike: float,
    etf_outflow_ratio: float,
    regime: MarketRegime,
) -> float:
    """طبقة التدفقات التي تقيس ضغط السيولة والبيع."""
    pressure = (
        max(0.0, open_interest_ratio - 1.0) * 0.4
        + max(0.0, volume_spike - 1.5) * 0.3
        + max(0.0, etf_outflow_ratio) * 0.3
    )
    multiplier = {
        MarketRegime.CRISIS: 0.15,
        MarketRegime.STRESS: 0.08,
        MarketRegime.NORMAL: 0.02,
    }[regime]
    return -pressure * multiplier


def ai_tech_model(
    ai_bubble_score: float,
    ai_earnings_surprise: float,
    ipo_sentiment: float,
    gold_ai_correlation: float,
    regime: MarketRegime,
) -> float:
    """طبقة مخاطر الذكاء الاصطناعي والتقييمات عالية النمو."""
    del regime  # الحالة محفوظة في التوقيع للتوافق مع تصميم الطبقات.
    direct = -ai_bubble_score * 0.05 + ai_earnings_surprise * 0.03
    crash_risk = 0.0
    if ai_bubble_score > 0.8 and ai_earnings_surprise < 0:
        crash_risk = (ai_bubble_score - 0.8) * gold_ai_correlation * 0.25
    return direct - crash_risk - ipo_sentiment * 0.02


def dynamic_weights(regime: MarketRegime) -> Dict[str, float]:
    """الأوزان التي تتغير مع شدة اضطراب السوق."""
    return {
        MarketRegime.NORMAL: {"economic": 0.60, "flow": 0.15, "ai": 0.25},
        MarketRegime.STRESS: {"economic": 0.40, "flow": 0.35, "ai": 0.25},
        MarketRegime.CRISIS: {"economic": 0.15, "flow": 0.60, "ai": 0.25},
    }[regime]


def forced_selling_radar(
    volume_spike: float,
    price_change: float,
    open_interest_ratio: float,
    sp500_change: float,
) -> Dict[str, Any]:
    """يرصد إشارات البيع القسري ويعيد حالة مفهومة للمستخدم."""
    score = 0
    if volume_spike > 2.0:
        score += 3
    elif volume_spike > 1.5:
        score += 2

    if price_change < -0.02:
        score += 2
    elif price_change < -0.01:
        score += 1

    if sp500_change < -0.03:
        score += 3
    elif sp500_change < -0.015:
        score += 2

    if open_interest_ratio > 1.5:
        score += 2

    if score >= 7:
        status, msg = "CRITICAL", "إشارات بيع قسري مرتفعة؛ راقب السيولة قبل اتخاذ أي قرار."
    elif score >= 4:
        status, msg = "WARNING", "توجد مؤشرات ضغط بيعي؛ خفّض حجم المخاطرة وراقب التأكيدات."
    else:
        status, msg = "CLEAR", "لا تظهر حالياً إشارات قوية على البيع القسري."
    return {"status": status, "score": score, "msg": msg}


def gold_x_model(data: Dict[str, Any]) -> Dict[str, Any]:
    """الدالة الرئيسية التي تجمع الطبقات وتنتج مخرجات لوحة التحكم."""
    regime = detect_regime(
        data["vix"],
        data["sp500_change_5d"],
        data["gold_equity_corr"],
        data["algo_intensity"],
        data["open_interest_ratio"],
    )
    economic = economic_model(
        data["dxy_change"],
        data["tip_change"],
        data["cpi_change"],
        data["fed_stance"],
        regime,
    )
    flow = flow_model(
        data["open_interest_ratio"],
        data["volume_spike"],
        data["etf_outflow_ratio"],
        regime,
    )
    ai = ai_tech_model(
        data["ai_bubble_score"],
        data["ai_earnings_surprise"],
        data["ipo_sentiment"],
        data["gold_ai_correlation"],
        regime,
    )
    weights = dynamic_weights(regime)
    change = economic * weights["economic"] + flow * weights["flow"] + ai * weights["ai"]
    radar = forced_selling_radar(
        data["volume_spike"],
        data["price_change"],
        data["open_interest_ratio"],
        data["sp500_change_5d"],
    )
    predicted_price = data["current_price"] * (1 + change)
    penalty = {
        MarketRegime.NORMAL: 0.0,
        MarketRegime.STRESS: -1.5,
        MarketRegime.CRISIS: -3.0,
    }[regime]
    confidence = min(10.0, max(0.0, abs(change) * 10 + penalty))

    if radar["status"] == "CRITICAL":
        recommendation = "⛔ لا تشترِ. انتظر 48–72 ساعة."
    elif change > 0.02 and confidence > 5:
        recommendation = "🟢 شراء (حسب خطة الدفعات)"
    elif change < -0.02 and confidence > 5:
        recommendation = "🔴 لا تشترِ الآن."
    else:
        recommendation = "🟡 انتظار / حياد"

    warnings = []
    if regime == MarketRegime.CRISIS:
        warnings.append("حالة السوق مصنفة كأزمة؛ تقل موثوقية الإشارات قصيرة الأجل.")
    elif regime == MarketRegime.STRESS:
        warnings.append("تقلبات السوق مرتفعة؛ استخدم أحجاماً صغيرة ونقاط خروج واضحة.")
    if radar["status"] != "CLEAR":
        warnings.append(radar["msg"])
    if data["volume_spike"] > 2:
        warnings.append("حجم التداول الحالي أعلى بكثير من متوسطه المتحرك.")

    return {
        "regime": regime.value,
        "change_pct": change,
        "predicted_price": predicted_price,
        "confidence": confidence,
        "recommendation": recommendation,
        "radar": radar,
        "warnings": warnings,
        "breakdown": {"economic": economic, "flow": flow, "ai": ai},
        "weights": weights,
    }
