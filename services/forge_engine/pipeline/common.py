from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from typing import Any


XML_TOKEN_RE = re.compile(r"[^a-z0-9_]+")


def json_default(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def stable_json(data: Any) -> str:
    return json.dumps(
        data,
        default=json_default,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def module_state_hash(module_state: Any) -> str:
    return hash_text(stable_json(module_state))


def xml_token(value: str | None) -> str:
    normalized = XML_TOKEN_RE.sub("_", (value or "").strip().lower()).strip("_")
    return normalized or "item"


def runtime_model_name(technical_name: str) -> str:
    candidate = f"x_{xml_token(technical_name.replace('.', '_'))}"
    return candidate[:63]


def runtime_field_name(field_name: str) -> str:
    candidate = field_name if field_name.startswith("x_") else f"x_{xml_token(field_name)}"
    return candidate[:63]


def runtime_relation_model_name(relation_model: str) -> str:
    if relation_model.startswith(("kodoo.", "app_", "x_")):
        return runtime_model_name(relation_model)
    if "." in relation_model and relation_model.replace(".", "_").replace("_", "").isalnum():
        return runtime_model_name(relation_model)
    return relation_model
