"""تخزين واسترجاع بيانات GOLD-X 2.0 محلياً عند تعذر المصادر الحية."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_DATA_FILE = PROJECT_ROOT / "data" / "market_data.json"
SCHEMA_VERSION = 1


def data_file_path() -> Path:
    """يعيد مسار التخزين، مع إمكانية تغييره في بيئات النشر."""
    configured = os.getenv("GOLD_X_DATA_FILE", "").strip()
    return Path(configured).expanduser() if configured else DEFAULT_DATA_FILE


def _json_safe(value: Any) -> Any:
    """تحويل أنواع NumPy/Pandas الشائعة إلى أنواع JSON قياسية."""
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    return value


def load_cached_data() -> Optional[Dict[str, Any]]:
    """قراءة آخر لقطة سليمة، مع رفض الملفات التالفة أو غير المتوافقة."""
    path = data_file_path()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or payload.get("schema_version") != SCHEMA_VERSION:
            return None
        data = payload.get("data")
        if not isinstance(data, dict) or not data.get("current_price"):
            return None
        data["storage_saved_at_utc"] = payload.get("saved_at_utc", "")
        data["storage_file"] = str(path)
        return data
    except (OSError, ValueError, TypeError):
        return None


def save_cached_data(data: Dict[str, Any]) -> bool:
    """حفظ لقطة مكتملة بعملية ذرّية حتى لا يقرأ التطبيق ملفاً نصف مكتوب."""
    path = data_file_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": SCHEMA_VERSION,
            "saved_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "data": _json_safe(data),
        }
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False
        ) as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, allow_nan=False)
            handle.write("\n")
            temporary_path = Path(handle.name)
        temporary_path.replace(path)
        return True
    except (OSError, TypeError, ValueError):
        try:
            if "temporary_path" in locals():
                temporary_path.unlink(missing_ok=True)
        except OSError:
            pass
        return False
