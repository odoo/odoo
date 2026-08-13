# -*- coding: utf-8 -*-
"""Reusable value transforms for config-driven imports."""

from datetime import date, datetime, timedelta

from odoo.exceptions import UserError


def header_key(value):
    return (value or "").strip().lower()


def parse_date_value(value, *, field_label):
    if value in (None, ""):
        raise UserError("%s is required in the uploaded file." % field_label)
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, (int, float)):
        excel_epoch = datetime(1899, 12, 30)
        return (excel_epoch + timedelta(days=float(value))).date()
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise UserError("Could not parse %s value '%s'." % (field_label, text))


def to_float_value(value, *, field_label):
    if value in (None, ""):
        return False
    text = str(value).replace(",", "").replace("$", "").strip()
    try:
        return float(text)
    except ValueError as exc:
        raise UserError("Could not parse %s value '%s' as a number." % (field_label, value)) from exc


def normalize_text(value):
    return str(value or "").strip() or False


def normalize_match_text(value):
    normalized = normalize_text(value)
    return normalized.casefold() if normalized else False


def normalize_time_value(value):
    if value in (None, ""):
        return False
    if isinstance(value, datetime):
        return value.strftime("%H:%M:%S")
    if isinstance(value, (int, float)):
        total_seconds = int(round(float(value) * 24 * 60 * 60))
        hours = (total_seconds // 3600) % 24
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    text = str(value).strip()
    if text.upper().endswith("XM"):
        text = f"{text[:-2]}AM"
    for fmt in ("%H:%M:%S", "%H:%M", "%I:%M:%S %p", "%I:%M %p", "%I:%M:%S%p", "%I:%M%p"):
        try:
            return datetime.strptime(text, fmt).strftime("%H:%M:%S")
        except ValueError:
            continue
    return text or False


def to_int_string_value(value, *, field_label):
    if value in (None, ""):
        return False
    text = str(value).replace(",", "").strip()
    if ":" in text:
        parts = text.split(":")
        if len(parts) == 2:
            minutes_text = parts[0].strip() or "0"
            seconds_text = parts[1].strip() or "0"
            try:
                total_seconds = int(minutes_text) * 60 + int(seconds_text)
                return str(total_seconds)
            except ValueError as exc:
                raise UserError("Could not parse %s value '%s' as a duration." % (field_label, value)) from exc
    try:
        return str(int(round(float(text))))
    except ValueError as exc:
        raise UserError("Could not parse %s value '%s' as a whole number." % (field_label, value)) from exc


def to_length_selection_value(value, *, field_label):
    normalized = to_int_string_value(value, field_label=field_label)
    if not normalized:
        return False
    return "v_%s" % normalized.lstrip("0") if normalized != "0" else False


def to_postlog_status_value(value):
    text = (str(value or "").strip().lower())
    mapping = {
        "aired": "aired",
        "credit": "credited",
        "credited": "credited",
        "credited - partial": "credited_partial",
        "credited_partial": "credited_partial",
        "credited partial": "credited_partial",
    }
    return mapping.get(text, "aired")


def to_postlog_mirror_status_value(value):
    text = (str(value or "").strip().lower())
    mapping = {
        "aired": "aired",
        "credit": "credited",
        "credited": "credited",
        "discrepancy": "discrepancy",
        "discrepancy - paid": "discrepancy_paid",
        "discrepancy_paid": "discrepancy_paid",
        "discrepancy paid": "discrepancy_paid",
    }
    return mapping.get(text, "aired")


def apply_transforms(value, transform_names, *, field_label):
    transformed = value
    for name in transform_names or []:
        if name == "parse_date":
            transformed = parse_date_value(transformed, field_label=field_label)
        elif name == "to_float":
            transformed = to_float_value(transformed, field_label=field_label)
        elif name == "normalize_time":
            transformed = normalize_time_value(transformed)
        elif name == "to_int_string":
            transformed = to_int_string_value(transformed, field_label=field_label)
        elif name == "to_length_selection":
            transformed = to_length_selection_value(transformed, field_label=field_label)
        elif name == "to_postlog_status":
            transformed = to_postlog_status_value(transformed)
        elif name == "to_postlog_mirror_status":
            transformed = to_postlog_mirror_status_value(transformed)
        elif name == "trim":
            transformed = normalize_text(transformed)
        else:
            raise UserError("Unsupported import transform '%s'." % name)
    return transformed
