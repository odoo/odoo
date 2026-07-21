# -*- coding: utf-8 -*-
"""Reusable Spot Data / Postlog matching helpers."""

from datetime import datetime, timedelta

from ..import_utils.transforms import normalize_text


_DAY_NUMBERS = {
    "mon": 0,
    "tue": 1,
    "wed": 2,
    "thu": 3,
    "fri": 4,
    "sat": 5,
    "sun": 6,
}


def parse_clock_start_number(clock_start_time):
    value = normalize_text(clock_start_time) or ""
    if value.startswith("v_") and value.endswith("am"):
        try:
            return int(value[2:-2])
        except ValueError:
            return 6
    return 6


def selection_display(record, field_name):
    selection = dict(record._fields[field_name].selection)
    return selection.get(getattr(record, field_name), "") if getattr(record, field_name) else ""


def rate_matches(row_rate, schedule_rate):
    if row_rate in (False, None) or schedule_rate in (False, None):
        return False
    return abs(float(row_rate) - float(schedule_rate)) < 0.01


def length_matches(spot_length, schedule_length):
    if not spot_length or not schedule_length:
        return False
    try:
        return int(str(spot_length).replace("v_", "")) == int(str(schedule_length).replace("v_", ""))
    except ValueError:
        return False


def network_name_matches(uploaded_network, program_name):
    return normalize_text(uploaded_network) == normalize_text(program_name)


def build_air_datetime(air_date, air_time, start_number):
    if not air_date or not air_time:
        return None
    parsed = None
    time_text = str(air_time).strip()
    for fmt in ("%H:%M:%S", "%H:%M", "%I:%M:%S %p", "%I:%M %p"):
        try:
            parsed = datetime.strptime(time_text, fmt)
            break
        except ValueError:
            continue
    if not parsed:
        return None
    air_dt = datetime(
        air_date.year,
        air_date.month,
        air_date.day,
        parsed.hour,
        parsed.minute,
        parsed.second,
    )
    if air_dt.hour < start_number:
        air_dt += timedelta(days=1)
    return air_dt


def schedule_allows_air_datetime(schedule, air_dt, start_number):
    if not air_dt or not schedule.week or not schedule.days_allowed or not schedule.start_time or not schedule.end_time:
        return False

    start_label = selection_display(schedule, "start_time")
    end_label = selection_display(schedule, "end_time")
    if not start_label or not end_label:
        return False

    start_parts = _parse_schedule_clock_label(start_label)
    end_parts = _parse_schedule_clock_label(end_label)

    for day in schedule.days_allowed:
        code = (day.code or day.name or "").strip().lower()[:3]
        if code not in _DAY_NUMBERS:
            continue
        schedule_day = schedule.week + timedelta(days=_DAY_NUMBERS[code])
        start_dt = datetime(
            schedule_day.year,
            schedule_day.month,
            schedule_day.day,
            start_parts[0],
            start_parts[1],
            0,
        )
        end_dt = datetime(
            schedule_day.year,
            schedule_day.month,
            schedule_day.day,
            end_parts[0],
            end_parts[1],
            0,
        )
        if start_parts[0] < start_number:
            start_dt += timedelta(days=1)
            end_dt += timedelta(days=1)
        if end_label == "12:00A":
            end_dt += timedelta(days=1)
        elif (end_parts[0], end_parts[1]) <= (start_parts[0], start_parts[1]):
            end_dt += timedelta(days=1)
        if start_dt < air_dt < end_dt:
            return True
    return False


def _parse_schedule_clock_label(label):
    normalized = label.strip().upper().replace(" ", "")
    if normalized.endswith("A") and not normalized.endswith("AM"):
        normalized = f"{normalized}M"
    elif normalized.endswith("P") and not normalized.endswith("PM"):
        normalized = f"{normalized}M"
    parsed = datetime.strptime(normalized, "%I:%M%p")
    return parsed.hour, parsed.minute
