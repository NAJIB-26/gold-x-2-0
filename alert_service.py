"""إرسال تقرير GOLD-X بالبريد باستخدام أسرار البيئة فقط."""
from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage
from typing import Any, Dict


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required secret: {name}")
    return value


def build_alert_message(data: Dict[str, Any], result: Dict[str, Any]) -> str:
    gap = result.get("opening_gap", {})
    quality = data.get("data_quality", "unknown")
    lines = [
        "GOLD-X 2.0 — تقرير ما قبل إغلاق السوق",
        "=" * 42,
        f"السعر الحالي: ${float(data['current_price']):,.2f}",
        f"التغير اليومي: {float(data.get('price_change', 0.0)) * 100:+.2f}%",
        f"مصدر البيانات: {data.get('data_source', 'غير محدد')} ({quality})",
        f"حالة السوق: {result.get('regime', 'غير محدد')}",
        f"التوصية التحليلية: {result.get('recommendation', 'غير محددة')}",
        "",
        "فجوة الافتتاح بعد نهاية الأسبوع/العطلة:",
    ]
    if gap.get("status") == "ESTIMATE":
        lines.extend(
            [
                f"الاتجاه الأرجح: {gap['direction']}",
                f"التغير المتوقع: {float(gap['expected_pct']) * 100:+.2f}%",
                f"النطاق المحتمل: {float(gap['lower_pct']) * 100:+.2f}% إلى {float(gap['upper_pct']) * 100:+.2f}%",
                f"احتمال الارتفاع: {float(gap['probability_up']) * 100:.0f}%",
                f"درجة الثقة: {float(gap['confidence']):.0f}/100",
            ]
        )
    else:
        lines.append(f"غير متاح: {gap.get('message', 'البيانات التاريخية غير كافية.')}")

    radar = result.get("radar", {})
    lines.extend(
        [
            "",
            f"رادار البيع القسري: {radar.get('status', 'غير محدد')} ({radar.get('score', 0)}/10)",
            str(radar.get("msg", "")),
            "",
            "هذا التقرير تحليلي وليس نصيحة استثمارية. تحقق من البيانات قبل اتخاذ أي قرار.",
        ]
    )
    return "\n".join(lines)


def send_alert(data: Dict[str, Any], result: Dict[str, Any]) -> None:
    host = _required("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    username = _required("SMTP_USERNAME")
    password = _required("SMTP_PASSWORD")
    recipient = _required("ALERT_EMAIL")

    message = EmailMessage()
    message["Subject"] = "GOLD-X | تقرير الذهب قبل إغلاق السوق"
    message["From"] = username
    message["To"] = recipient
    message.set_content(build_alert_message(data, result))

    with smtplib.SMTP(host, port, timeout=30) as smtp:
        smtp.starttls()
        smtp.login(username, password)
        smtp.send_message(message)


if __name__ == "__main__":
    from data_fetcher import fetch_live_data
    from model import gold_x_model

    market_data = fetch_live_data()
    if market_data is None:
        raise RuntimeError("تعذر جلب بيانات الذهب")
    send_alert(market_data, gold_x_model(market_data))
    print("GOLD-X alert sent successfully")
