# -*- coding: utf-8 -*-
"""Config-driven Prelog import engine."""

import base64
import re
from datetime import datetime, time, timedelta

from odoo.exceptions import UserError

from .config_loader import load_program_config
from .parsers import read_tabular_rows
from .transforms import (
    apply_transforms,
    header_key,
    normalize_match_text,
    normalize_text,
    normalize_time_value,
)


class PrelogImportEngine:
    """Normalize uploaded files into mv.prelog_data values."""

    _DEFAULT_FIELD_MAP = {
        "week": ["Week"],
        "isci": ["ISCI"],
        "airdate": ["Air_Date", "Air Date"],
        "scheduletime": ["Air_Time", "Air Time", "Sched Time"],
        "network": ["Network"],
        "broadcast_network": ["Network"],
        "network_deal_number": ["Network Deal Number", "Deal/Order #", "Deal/Order#"],
        "agency": ["Advertiser", "Agency"],
        "advertiserproduct": ["Advertiser/Product", "Advertiser Product"],
        "materialdescription": ["Brand", "Material Description"],
        "orderproductdescription": ["Product", "Order Product Description"],
        "scheduleadid": ["Sched Ad-ID", "Sched Ad ID", "Schedule Ad-ID"],
        "schedulelength": ["Sched Length", "Schedule Length"],
        "timeperiod": ["Time Period"],
        "title": ["Program", "Title"],
        "rate": ["Booked_Rate", "Booked Rate", "Rate"],
    }
    _DEFAULT_TRANSFORMS = {
        "week": ["parse_date"],
        "airdate": ["parse_date"],
        "scheduletime": ["normalize_time"],
        "rate": ["to_float"],
        "schedulelength": ["to_int_string"],
        "isci": ["trim"],
        "network": ["trim"],
        "broadcast_network": ["trim"],
        "network_deal_number": ["trim"],
        "agency": ["trim"],
        "advertiserproduct": ["trim"],
        "materialdescription": ["trim"],
        "orderproductdescription": ["trim"],
        "scheduleadid": ["trim"],
        "timeperiod": ["trim"],
        "title": ["trim"],
    }
    _DEFAULT_REQUIRED_FIELDS = []
    _MATCHED = "matched"
    _CREATED_WITHOUT_SCHEDULE = "created_without_schedule"
    _FAILED_TO_CREATE = "failed_to_create"
    _START_NUMBER_DEFAULT = 6
    _DAY_NUMBERS = {
        "mon": 0,
        "tue": 1,
        "wed": 2,
        "thu": 3,
        "fri": 4,
        "sat": 5,
        "sun": 6,
    }

    def __init__(self, env, *, program, upload_file, upload_filename):
        self.env = env
        self.program = program
        self.upload_file = upload_file
        self.upload_filename = (upload_filename or "").strip()
        self.config = load_program_config(program.display_name if program else "")

    def decode_upload(self):
        if not self.upload_file:
            raise UserError("Upload a file first.")
        try:
            return base64.b64decode(self.upload_file), self.upload_filename
        except Exception as exc:
            raise UserError("Could not decode the uploaded file: %s" % exc) from exc

    def extract_rows_and_week(self):
        payload, filename = self.decode_upload()
        raw_rows = read_tabular_rows(payload, filename, self.config)
        if not raw_rows:
            raise UserError("The uploaded file has no data rows.")

        normalized_rows = []
        for row in raw_rows:
            if self._is_non_data_row(row):
                continue
            normalized_rows.append(self._normalize_row(row))
        if not normalized_rows:
            raise UserError("The uploaded file has no usable data rows.")
        detected_weeks = []
        for row in normalized_rows:
            detected_weeks.append(self._detect_week(row))

        unique_weeks = sorted(set(detected_weeks))
        if len(unique_weeks) != 1:
            raise UserError("The uploaded file must contain exactly one Week.")

        return normalized_rows, unique_weeks[0]

    def build_prelog_vals(self, rows, import_week, version):
        vals_list = []
        summary = {
            self._MATCHED: 0,
            self._CREATED_WITHOUT_SCHEDULE: 0,
            self._FAILED_TO_CREATE: 0,
        }
        for row_index, row in enumerate(rows, start=self._first_data_row_number()):
            vals = self._build_row_vals(row, import_week, version, row_index)
            summary[vals["import_match_status"]] += 1
            vals_list.append(vals)
        return vals_list, summary

    def build_row_vals(self, row, import_week, version, row_index):
        return self._build_row_vals(row, import_week, version, row_index)

    def export_field_names(self):
        return list(self._field_map().keys())

    def _normalize_row(self, row):
        normalized = {}
        for canonical_name, candidates in self._field_map().items():
            normalized[canonical_name] = self._first_value(row, candidates)
        for required_field in self._required_fields():
            if normalized.get(required_field) in (None, ""):
                raise UserError("Required field '%s' is missing from the uploaded file." % required_field)
        return normalized

    def _field_map(self):
        field_map = dict(self._DEFAULT_FIELD_MAP)
        field_map.update(self.config.get("fieldMap", {}))
        return field_map

    def _required_fields(self):
        return self.config.get("requiredFields", list(self._DEFAULT_REQUIRED_FIELDS))

    def _is_non_data_row(self, row):
        identifying_fields = (
            "airdate",
            "scheduletime",
            "network_deal_number",
            "title",
            "agency",
            "advertiserproduct",
            "orderproductdescription",
            "network",
            "broadcast_network",
        )
        for field_name in identifying_fields:
            candidates = self._field_map().get(field_name, [])
            if self._first_value(row, candidates) not in (None, ""):
                return False
        return True

    def _detect_week(self, row):
        week_value = row.get("week")
        if week_value not in (None, ""):
            return self._transform_value("week", week_value)

        if self.config.get("deriveWeekFromAirdate"):
            airdate_value = row.get("airdate")
            if airdate_value in (None, ""):
                raise UserError("Every uploaded row must include an Air Date value to derive the import week.")
            airdate = self._transform_value("airdate", airdate_value)
            return airdate - timedelta(days=airdate.weekday())

        raise UserError("Every uploaded row must include a Week value.")

    def _transform_value(self, field_name, value):
        transforms = dict(self._DEFAULT_TRANSFORMS)
        transforms.update(self.config.get("transforms", {}))
        return apply_transforms(
            value,
            transforms.get(field_name, []),
            field_label=field_name.replace("_", " ").title(),
        )

    def _optional_value(self, field_name, value):
        if value in (None, ""):
            return False
        transformed = self._transform_value(field_name, value)
        return transformed if transformed not in ("", None) else False

    @classmethod
    def _sanitize_stored_schedule_time(cls, *, parsed_value, raw_value):
        value = parsed_value
        if value in (None, False, ""):
            raw_text = normalize_text(raw_value)
            if raw_text and "XM" in raw_text.upper():
                value = (
                    normalize_time_value(raw_text)
                    or raw_text.replace("XM", "AM").replace("xm", "AM")
                )
        parsed_time = cls._parse_time(value)
        if parsed_time:
            return parsed_time.strftime("%I:%M:%S %p").lstrip("0")
        return value

    def _safe_optional_value(self, field_name, value, errors):
        if value in (None, ""):
            return False
        try:
            return self._optional_value(field_name, value)
        except UserError as exc:
            errors.append(str(exc))
            return False

    @staticmethod
    def _first_value(row, candidates):
        for candidate in candidates:
            normalized_candidate = header_key(candidate)
            for key, value in row.items():
                if header_key(key) == normalized_candidate and value not in (None, ""):
                    return value
        return None

    def _build_row_vals(self, row, import_week, version, row_index):
        parse_errors = []
        airdate = self._safe_optional_value("airdate", row.get("airdate"), parse_errors)
        scheduletime = self._safe_optional_value("scheduletime", row.get("scheduletime"), parse_errors)
        scheduletime = self._sanitize_stored_schedule_time(
            parsed_value=scheduletime,
            raw_value=row.get("scheduletime"),
        )
        rate = self._safe_optional_value("rate", row.get("rate"), parse_errors)
        schedulelength = self._safe_optional_value("schedulelength", row.get("schedulelength"), parse_errors)

        match_outcome = self._match_schedule(
            row=row,
            import_week=import_week,
            row_index=row_index,
            airdate=airdate,
            scheduletime=scheduletime,
            rate=rate,
            schedulelength=schedulelength,
        )

        detail_parts = list(parse_errors)
        if match_outcome["detail"]:
            detail_parts.append(match_outcome["detail"])

        return {
            "schedule": match_outcome["schedule_id"],
            "version": version,
            "isci": self._first_non_empty(
                normalize_text(row.get("isci")),
                normalize_text(row.get("scheduleadid")),
            ),
            "airdate": airdate,
            "scheduletime": scheduletime,
            "schedulelength": schedulelength,
            "scheduleadid": self._safe_optional_value("scheduleadid", row.get("scheduleadid"), parse_errors),
            "network": self.program.display_name if self.program else False,
            "broadcast_network": self._safe_optional_value("broadcast_network", row.get("broadcast_network"), parse_errors),
            "network_deal_number": self._safe_optional_value("network_deal_number", row.get("network_deal_number"), parse_errors),
            "agency": self._safe_optional_value("agency", row.get("agency"), parse_errors),
            "advertiserproduct": self._safe_optional_value("advertiserproduct", row.get("advertiserproduct"), parse_errors),
            "materialdescription": self._safe_optional_value("materialdescription", row.get("materialdescription"), parse_errors),
            "orderproductdescription": self._safe_optional_value("orderproductdescription", row.get("orderproductdescription"), parse_errors),
            "timeperiod": self._safe_optional_value("timeperiod", row.get("timeperiod"), parse_errors),
            "title": self._safe_optional_value("title", row.get("title"), parse_errors),
            "rate": rate,
            "batch_id": self.upload_filename or False,
            "import_program": self.program.id,
            "import_week_value": import_week,
            "import_match_status": match_outcome["status"],
            "import_match_detail": "; ".join(part for part in detail_parts if part) or False,
        }

    def _match_schedule(self, *, row, import_week, row_index, airdate, scheduletime, rate, schedulelength):
        report = _ErrorReport()
        network_deal_number = normalize_text(row.get("network_deal_number"))
        if not network_deal_number:
            report.invalid_network_deal_number = True
            return self._unmatched_outcome(report)

        deals = self.env["mv.deal"].search(
            [
                ("program", "=", self.program.id),
                ("network_deal_number", "=", network_deal_number),
            ],
            order="id",
        )
        if not deals:
            report.network_deal_number_not_found = True
            return self._unmatched_outcome(report)

        for deal in deals:
            deal_report = _ErrorReport()
            if not self._has_network_match(row, deal, deal_report):
                report.merge(deal_report)
                continue

            start_number = self._get_start_number(deal.program)
            schedules = self.env["mv.schedules"].search(
                [
                    ("deal_parent", "=", deal.id),
                    ("status", "=", "sold"),
                ],
                order="id",
            )
            for schedule in schedules:
                schedule_report = _ErrorReport()
                if (
                    self._has_valid_unit_length(schedulelength, schedule, schedule_report)
                    and self._has_valid_airdate(
                        airdate=airdate,
                        scheduletime=scheduletime,
                        schedule=schedule,
                        report=schedule_report,
                        start_number=start_number,
                    )
                    and self._has_valid_rate(rate, schedule, schedule_report)
                ):
                    return {
                        "status": self._MATCHED,
                        "detail": False,
                        "schedule_id": schedule.id,
                    }
                report.merge(schedule_report)

        return self._unmatched_outcome(report, row_index=row_index)

    def _unmatched_outcome(self, report, row_index=None):
        detail = report.as_string()
        if row_index and detail:
            detail = "Row %s: %s" % (row_index, detail)
        return {
            "status": self._CREATED_WITHOUT_SCHEDULE,
            "detail": detail or "No matching sold schedule was found.",
            "schedule_id": False,
        }

    def _has_network_match(self, row, deal, report):
        row_network = normalize_match_text(row.get("network"))
        if row_network and row_network not in self._network_names_for_match(deal):
            report.network_deal_number_not_found = True
            return False
        return True

    @staticmethod
    def _has_valid_unit_length(schedulelength, schedule, report):
        schedule_unit_length = PrelogImportEngine._schedule_unit_length(schedule)
        if schedule_unit_length is None or schedulelength in (None, False, ""):
            report.unit_length_not_found = True
            return False
        try:
            return int(schedule_unit_length) == int(schedulelength)
        except (TypeError, ValueError):
            report.unit_length_not_found = True
            return False

    @staticmethod
    def _has_valid_rate(rate, schedule, report):
        if schedule.rate is not None and rate is not None and float(schedule.rate) == float(rate):
            return True
        report.rate_not_found = True
        return False

    def _has_valid_airdate(self, *, airdate, scheduletime, schedule, report, start_number):
        if not airdate or not schedule.days_allowed:
            report.air_date_not_found = True
            return False

        allowed_days = {normalize_text(tag.name)[:3].lower() for tag in schedule.days_allowed if tag.name}
        weekday_code = airdate.strftime("%a").lower()
        if weekday_code not in allowed_days:
            report.air_date_not_valid = True
            return False

        if not scheduletime:
            report.air_time_not_found = True
            return False

        air_datetime = self._air_datetime(airdate, scheduletime, start_number)
        if not air_datetime:
            report.air_time_not_found = True
            return False

        if not schedule.week or not schedule.start_time or not schedule.end_time:
            report.air_time_not_found = True
            return False

        if not self._is_valid_schedule_window(schedule, start_number, air_datetime):
            report.air_time_not_found = True
            return False
        return True

    def _is_valid_schedule_window(self, schedule, start_number, air_datetime):
        for day in schedule.days_allowed:
            day_code = normalize_text(day.name)[:3].lower()
            day_offset = self._DAY_NUMBERS.get(day_code)
            if day_offset is None:
                continue

            start_time = self._selection_label(schedule, "start_time")
            end_time = self._selection_label(schedule, "end_time")
            if not start_time or not end_time:
                continue

            start_dt = self._schedule_datetime(schedule.week, day_offset, start_time)
            end_dt = self._schedule_datetime(schedule.week, day_offset, end_time)
            if not start_dt or not end_dt:
                continue

            if end_time == "12:00A":
                end_dt += timedelta(days=1)

            if start_dt.hour < start_number:
                start_dt += timedelta(days=1)
                end_dt += timedelta(days=1)

            if end_dt <= start_dt and end_time != "12:00A":
                end_dt += timedelta(days=1)

            if start_dt <= air_datetime <= end_dt:
                return True
        return False

    def _air_datetime(self, airdate, scheduletime, start_number):
        time_value = self._parse_time(scheduletime)
        if not time_value:
            return None
        air_datetime = datetime.combine(airdate, time_value)
        if air_datetime.hour < start_number:
            air_datetime += timedelta(days=1)
        return air_datetime

    def _schedule_datetime(self, week_date, day_offset, time_label):
        time_value = self._parse_time(time_label)
        if not time_value:
            return None
        return datetime.combine(week_date + timedelta(days=day_offset), time_value)

    def _get_start_number(self, program):
        label = self._selection_label(program, "clock_start_time")
        if label:
            match = re.search(r"(\d+)", label)
            if match:
                return int(match.group(1))
        return self._START_NUMBER_DEFAULT

    @staticmethod
    def _parse_time(value):
        if value in (None, False, ""):
            return None
        text = str(value).strip().upper().replace(" ", "")
        if text.endswith("A") and not text.endswith("AM"):
            text = f"{text}M"
        elif text.endswith("P") and not text.endswith("PM"):
            text = f"{text}M"
        for fmt in ("%H:%M:%S", "%H:%M", "%I:%M:%S%p", "%I:%M%p"):
            try:
                return datetime.strptime(text, fmt).time()
            except ValueError:
                continue
        return None

    @staticmethod
    def _selection_label(record, field_name):
        if not record or not record[field_name]:
            return False
        selection = dict(record._fields[field_name].selection)
        return selection.get(record[field_name], record[field_name])

    @staticmethod
    def _first_non_empty(*values):
        for value in values:
            if value not in (None, False, ""):
                return value
        return False

    def _first_data_row_number(self):
        return int(self.config.get("headerRow", 1)) + 2

    def _network_names_for_match(self, deal):
        names = set()
        config_names = self.config.get("networkNames", [])
        for value in config_names:
            normalized = normalize_match_text(value)
            if normalized:
                names.add(normalized)
        if deal.program and deal.program.display_name:
            names.add(normalize_match_text(deal.program.display_name))
        return names

    @staticmethod
    def _schedule_unit_length(schedule):
        if schedule.unitlength not in (None, False, ""):
            return schedule.unitlength
        if schedule.deal_parent and schedule.deal_parent.length:
            label = PrelogImportEngine._selection_label(schedule.deal_parent, "length")
            if label:
                try:
                    return int(label)
                except (TypeError, ValueError):
                    return None
        return None


class _ErrorReport:
    def __init__(self):
        self.invalid_network_deal_number = False
        self.network_deal_number_not_found = False
        self.unit_length_not_found = False
        self.air_date_not_found = False
        self.air_date_not_valid = False
        self.air_time_not_found = False
        self.rate_not_found = False

    def merge(self, other):
        self.invalid_network_deal_number = self.invalid_network_deal_number or other.invalid_network_deal_number
        self.network_deal_number_not_found = self.network_deal_number_not_found or other.network_deal_number_not_found
        self.unit_length_not_found = self.unit_length_not_found or other.unit_length_not_found
        self.air_date_not_found = self.air_date_not_found or other.air_date_not_found
        self.air_date_not_valid = self.air_date_not_valid or other.air_date_not_valid
        self.air_time_not_found = self.air_time_not_found or other.air_time_not_found
        self.rate_not_found = self.rate_not_found or other.rate_not_found

    def as_string(self):
        errors = []
        if self.invalid_network_deal_number:
            errors.append("Invalid Network Deal Number")
        if self.network_deal_number_not_found:
            errors.append("Network Deal Number Not Found")
        if self.air_date_not_found:
            errors.append("Air Date Not Found")
        if self.air_date_not_valid:
            errors.append("Air Date Not Valid")
        if self.air_time_not_found:
            errors.append("Air Time Not Found")
        if self.unit_length_not_found:
            errors.append("Unit Length Not Found")
        if self.rate_not_found:
            errors.append("Rate Not Found")
        return ", ".join(errors)
