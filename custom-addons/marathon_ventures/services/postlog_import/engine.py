# -*- coding: utf-8 -*-
"""Config-driven Postlog import engine."""

import base64
from datetime import timedelta

from odoo.exceptions import UserError

from .config_loader import load_program_config
from .matchers import (
    build_air_datetime,
    length_matches,
    network_name_matches,
    parse_clock_start_number,
    rate_matches,
    schedule_allows_air_datetime,
)
from ..import_utils.parsers import read_tabular_rows
from ..import_utils.transforms import apply_transforms, header_key


class PostlogImportEngine:
    """Normalize uploaded files into mv.spot_data values."""

    _DEFAULT_FIELD_MAP = {
        "week": ["Week"],
        "air_date": ["Air_Date", "Air Date", "Date"],
        "air_time": ["Air_Time", "Air Time", "Time"],
        "agency": ["Agency"],
        "aired_ad_id": ["Aired Ad-ID", "Aired Ad ID"],
        "isci": ["ISCI", "Ad ID", "Ad-ID", "Ad Id"],
        "length": ["Length", "Spot Length", "Commercial Length"],
        "materialdescription": ["Material Description"],
        "network": ["Network"],
        "broadcast_network": ["Broadcast Network", "Network"],
        "network_deal_number": ["Network Deal Number", "Deal/Order #", "Deal/Order#", "Order Number"],
        "orderproductdescription": ["Order Product Description"],
        "spot_rate": ["Rate", "Spot Rate"],
        "line_number": ["Line Number", "Line #"],
        "commercial_title": ["Commercial Title", "Brand", "Material Description"],
        "product": ["Product", "Advertiser/Product", "Advertiser Product"],
        "program": ["Program"],
        "time_period": ["Time Period"],
        "x800": ["800 #", "800#", "x800"],
        "status": ["Status"],
        "raycom_invoice_number": ["Invoice Number", "Raycom Invoice Number"],
        "program_id": ["Program ID"],
        "log_schedule": ["Log Schedule", "Schedule"],
    }
    _DEFAULT_TRANSFORMS = {
        "week": ["parse_date"],
        "air_date": ["parse_date"],
        "air_time": ["normalize_time"],
        "agency": ["trim"],
        "aired_ad_id": ["trim"],
        "isci": ["trim"],
        "length": ["to_length_selection"],
        "materialdescription": ["trim"],
        "network": ["trim"],
        "broadcast_network": ["trim"],
        "network_deal_number": ["trim"],
        "orderproductdescription": ["trim"],
        "spot_rate": ["to_float"],
        "line_number": ["trim"],
        "commercial_title": ["trim"],
        "product": ["trim"],
        "program": ["trim"],
        "time_period": ["trim"],
        "x800": ["trim"],
        "status": ["to_postlog_status"],
        "raycom_invoice_number": ["trim"],
        "program_id": ["trim"],
        "log_schedule": ["trim"],
    }
    _DEFAULT_REQUIRED_FIELDS = ["air_date", "air_time", "network_deal_number"]

    # Mirrors PrelogImportEngine's status vocabulary so both jobs report the
    # same three outcomes into `import_match_status`.
    _MATCHED = "matched"
    _CREATED_WITHOUT_SCHEDULE = "created_without_schedule"
    _FAILED_TO_CREATE = "failed_to_create"

    def __init__(self, env, *, program, upload_file, upload_filename):
        self.env = env
        self.program = program
        self.upload_file = upload_file
        self.upload_filename = (upload_filename or "").strip()
        self.config = load_program_config(program.display_name if program else "")
        # Rows dropped by _should_skip_row; surfaced on the import job so blank
        # or unusable rows are reported instead of quietly disappearing.
        self.skipped_row_count = 0

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
        skipped_row_count = 0
        first_data_row = self._first_data_row_number()
        for offset, row in enumerate(raw_rows):
            row_number = first_data_row + offset
            if self._should_skip_row(row):
                skipped_row_count += 1
                continue
            normalized_rows.append(self._normalize_row(row, row_number=row_number))
        if not normalized_rows:
            raise UserError("The uploaded file has no importable data rows.")
        self.skipped_row_count = skipped_row_count

        # Week detection reports its own row number too, so "one Week" failures
        # point at a spreadsheet row instead of the whole file.
        weeks_by_row = {}
        for row, row_number in zip(normalized_rows, self._data_row_numbers(raw_rows)):
            weeks_by_row[row_number] = self._detect_week(row, row_number=row_number)
        unique_weeks = sorted(set(weeks_by_row.values()))
        if len(unique_weeks) != 1:
            sample = ', '.join(
                '%s (row %s)' % (week, min(r for r, w in weeks_by_row.items() if w == week))
                for week in unique_weeks[:4]
            )
            raise UserError(
                "The uploaded file must contain exactly one Week, but %s were found: %s."
                % (len(unique_weeks), sample)
            )

        return normalized_rows, unique_weeks[0]

    def _data_row_numbers(self, raw_rows):
        """Spreadsheet row numbers of the rows that survived _should_skip_row."""
        first_data_row = self._first_data_row_number()
        return [
            first_data_row + offset
            for offset, row in enumerate(raw_rows)
            if not self._should_skip_row(row)
        ]

    def import_rows(self, rows, import_week):
        SpotData = self.env["mv.spot_data"]
        summary = {
            "spot_created": 0,
            "matched": 0,
            "unmatched": 0,
            "errors": [],
        }

        for row_index, row in enumerate(rows, start=self._first_data_row_number()):
            spot_vals, outcome = self._build_row_payload(row, import_week, row_index)
            try:
                if spot_vals:
                    SpotData.create(spot_vals)
                    summary["spot_created"] += 1
                    if outcome:
                        summary["unmatched"] += 1
                        summary["errors"].append("Row %s: %s" % (row_index, outcome))
                    else:
                        summary["matched"] += 1
                else:
                    summary["unmatched"] += 1
                    if outcome:
                        summary["errors"].append("Row %s: %s" % (row_index, outcome))
            except Exception as exc:
                summary["errors"].append("Row %s: %s" % (row_index, exc))
        return summary

    def build_row_vals(self, row, import_week, row_index):
        """Return mv.spot_data values for one normalized row.

        Mirrors PrelogImportEngine.build_row_vals. Parse failures are collected
        into `import_match_detail` rather than aborting the whole upload, so one
        malformed cell cannot cost the operator the other 2,000 rows.
        """
        parse_errors = []
        air_date = self._safe_optional_value("air_date", row.get("air_date"), parse_errors)
        air_time = self._safe_optional_value("air_time", row.get("air_time"), parse_errors)
        length = self._safe_optional_value("length", row.get("length"), parse_errors)
        length = self._coerce_selection("length", length, parse_errors, "Aired Length")
        spot_rate = self._safe_optional_value("spot_rate", row.get("spot_rate"), parse_errors)
        network_deal_number = self._safe_optional_value("network_deal_number", row.get("network_deal_number"), parse_errors)
        status = self._safe_optional_value("status", row.get("status"), parse_errors) or "aired"
        status = self._coerce_selection("status", status, parse_errors, "Status") or "aired"
        selected_program_name = self._selected_program_name()
        broadcast_network = (
            selected_program_name
            if self.config.get("useProgramForNetwork")
            else self._safe_optional_value("broadcast_network", row.get("broadcast_network"), parse_errors)
        )

        schedule, match_detail = self._match_schedule(
            network=(
                selected_program_name
                if self.config.get("useProgramForNetwork")
                else self._safe_optional_value("network", row.get("network"), parse_errors) or selected_program_name
            ),
            network_deal_number=network_deal_number,
            air_date=air_date,
            air_time=air_time,
            length=length,
            spot_rate=spot_rate,
            import_week=import_week,
        )

        detail_parts = list(parse_errors)
        if match_detail:
            detail_parts.append(match_detail)

        return {
            "schedule": schedule.id if schedule else False,
            "air_date": air_date,
            "air_time": air_time,
            "length": length,
            "spot_rate": spot_rate,
            "isci": self._safe_optional_value("isci", row.get("isci"), parse_errors),
            "aired_ad_id": self._safe_optional_value("aired_ad_id", row.get("aired_ad_id"), parse_errors),
            "broadcast_network": broadcast_network,
            "network_deal_number": network_deal_number,
            "raycom_order_number": network_deal_number,
            "agency": self._safe_optional_value("agency", row.get("agency"), parse_errors),
            "commercial_title": self._safe_optional_value("commercial_title", row.get("commercial_title"), parse_errors),
            "materialdescription": self._safe_optional_value("materialdescription", row.get("materialdescription"), parse_errors),
            "orderproductdescription": self._safe_optional_value("orderproductdescription", row.get("orderproductdescription"), parse_errors),
            "product": self._safe_optional_value("product", row.get("product"), parse_errors),
            "program": self._safe_optional_value("program", row.get("program"), parse_errors),
            "program_id": self._safe_optional_value("program_id", row.get("program_id"), parse_errors),
            "line_number": self._safe_optional_value("line_number", row.get("line_number"), parse_errors),
            "time_period": self._safe_optional_value("time_period", row.get("time_period"), parse_errors),
            "raycom_invoice_number": self._safe_optional_value("raycom_invoice_number", row.get("raycom_invoice_number"), parse_errors),
            "x800": self._safe_optional_value("x800", row.get("x800"), parse_errors),
            "status": status,
            "batch_id": self.upload_filename or False,
            "import_program": self.program.id if self.program else False,
            "import_week_value": import_week,
            "import_match_status": self._MATCHED if schedule else self._CREATED_WITHOUT_SCHEDULE,
            "import_match_detail": "; ".join(part for part in detail_parts if part) or False,
        }

    def export_field_names(self):
        return list(self._field_map().keys())

    def _coerce_selection(self, field_name, value, errors, label):
        """Blank out a value the mv.spot_data Selection does not accept.

        mv.spot_data.length and mv.deal.length do not carry the same value set
        (mv.deal has v_20, v_25, v_35, v_40, v_105, v_150, v_240 and others that
        mv.spot_data lacks), so a perfectly ordinary spot length can produce a
        key the field rejects. Writing it would raise ValueError inside create()
        and cost the whole row. Blanking it and recording why keeps the row, and
        the operator sees it in the workbench as an unmatched spot with a
        readable reason instead of an entry in errors.csv.
        """
        if value in (None, False, ""):
            return False
        field = self.env["mv.spot_data"]._fields.get(field_name)
        if not field or field.type != "selection":
            return value
        selection = field.selection
        if callable(selection):
            selection = selection(self.env["mv.spot_data"])
        allowed = {key for key, _label in selection}
        if value in allowed:
            return value
        errors.append(
            "%s value %r is not one of the accepted values for this field, so it "
            "was left blank." % (label, value)
        )
        return False

    def _safe_optional_value(self, field_name, value, errors):
        if value in (None, ""):
            return False
        try:
            return self._optional_value(field_name, value)
        except UserError as exc:
            errors.append(str(exc))
            return False

    def _normalize_row(self, row, row_number=None):
        normalized = {}
        for canonical_name, candidates in self._field_map().items():
            normalized[canonical_name] = self._first_value(row, candidates)
        for required_field in self._required_fields():
            if normalized.get(required_field) in (None, ""):
                where = " (row %s)" % row_number if row_number else ""
                raise UserError(
                    "Required field '%s' is missing from the uploaded file%s. "
                    "Every row needs %s; fix that row or remove it, then upload again."
                    % (required_field, where, ", ".join(self._required_fields()))
                )
        return normalized

    def _field_map(self):
        field_map = dict(self._DEFAULT_FIELD_MAP)
        field_map.update(self.config.get("fieldMap", {}))
        return field_map

    def _required_fields(self):
        return self.config.get("requiredFields", list(self._DEFAULT_REQUIRED_FIELDS))

    def _should_skip_row(self, row):
        normalized = {}
        for canonical_name, candidates in self._field_map().items():
            normalized[canonical_name] = self._first_value(row, candidates)
        return all(normalized.get(required_field) in (None, "") for required_field in self._required_fields())

    def _detect_week(self, row, row_number=None):
        week_value = row.get("week")
        if week_value not in (None, ""):
            return self._transform_value("week", week_value)

        if self.config.get("deriveWeekFromAirDate", True):
            air_date_value = row.get("air_date")
            if air_date_value in (None, ""):
                raise UserError(
                    "Every uploaded row must include an Air Date value to derive "
                    "the import week%s." % (" (row %s)" % row_number if row_number else "")
                )
            try:
                air_date = self._transform_value("air_date", air_date_value)
            except UserError as exc:
                raise UserError(
                    "%s%s" % (exc, " (row %s)" % row_number if row_number else "")
                ) from exc
            return air_date - timedelta(days=air_date.weekday())

        raise UserError(
            "Every uploaded row must include a Week value%s."
            % (" (row %s)" % row_number if row_number else "")
        )

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

    def _selected_program_name(self):
        return getattr(self.program, "display_name", False) or getattr(self.program, "name", False) or False

    @staticmethod
    def _first_value(row, candidates):
        for candidate in candidates:
            normalized_candidate = header_key(candidate)
            for key, value in row.items():
                if header_key(key) == normalized_candidate and value not in (None, ""):
                    return value
        return None

    def _build_row_payload(self, row, import_week, row_index):
        air_date = self._optional_value("air_date", row.get("air_date"))
        air_time = self._optional_value("air_time", row.get("air_time"))
        network_deal_number = self._optional_value("network_deal_number", row.get("network_deal_number"))
        length = self._optional_value("length", row.get("length"))
        spot_rate = self._optional_value("spot_rate", row.get("spot_rate"))
        isci = self._optional_value("isci", row.get("isci"))
        status = self._optional_value("status", row.get("status")) or "aired"
        selected_program_name = self._selected_program_name()
        broadcast_network = (
            selected_program_name
            if self.config.get("useProgramForNetwork")
            else self._optional_value("broadcast_network", row.get("broadcast_network"))
        )
        network = (
            selected_program_name
            if self.config.get("useProgramForNetwork")
            else self._optional_value("network", row.get("network")) or selected_program_name
        )
        schedule, match_detail = self._match_schedule(
            network=network,
            network_deal_number=network_deal_number,
            air_date=air_date,
            air_time=air_time,
            length=length,
            spot_rate=spot_rate,
            import_week=import_week,
        )

        if not schedule:
            unmatched_vals = {
                "air_date": air_date,
                "air_time": air_time,
                "agency": self._optional_value("agency", row.get("agency")),
                "aired_ad_id": self._optional_value("aired_ad_id", row.get("aired_ad_id")),
                "broadcast_network": broadcast_network,
                "commercial_title": self._optional_value("commercial_title", row.get("commercial_title")),
                "error_mirror": match_detail or False,
                "isci": isci,
                "length": length,
                "line_number": self._optional_value("line_number", row.get("line_number")),
                "materialdescription": self._optional_value("materialdescription", row.get("materialdescription")),
                "network_deal_number": network_deal_number,
                "orderproductdescription": self._optional_value("orderproductdescription", row.get("orderproductdescription")),
                "product": self._optional_value("product", row.get("product")),
                "program": self._optional_value("program", row.get("program")),
                "program_id": self._optional_value("program_id", row.get("program_id")),
                "raycom_invoice_number": self._optional_value("raycom_invoice_number", row.get("raycom_invoice_number")),
                "raycom_order_number": network_deal_number,
                "spot_rate": spot_rate,
                "status": status,
                "time_period": self._optional_value("time_period", row.get("time_period")),
                "x800": self._optional_value("x800", row.get("x800")),
            }
            return unmatched_vals, match_detail

        spot_vals = {
            "air_date": air_date,
            "air_time": air_time,
            "agency": self._optional_value("agency", row.get("agency")),
            "aired_ad_id": self._optional_value("aired_ad_id", row.get("aired_ad_id")),
            "broadcast_network": broadcast_network,
            "commercial_title": self._optional_value("commercial_title", row.get("commercial_title")),
            "isci": isci,
            "length": length,
            "line_number": self._optional_value("line_number", row.get("line_number")),
            "materialdescription": self._optional_value("materialdescription", row.get("materialdescription")),
            "network_deal_number": network_deal_number,
            "orderproductdescription": self._optional_value("orderproductdescription", row.get("orderproductdescription")),
            "product": self._optional_value("product", row.get("product")),
            "program": self._optional_value("program", row.get("program")),
            "program_id": self._optional_value("program_id", row.get("program_id")),
            "raycom_invoice_number": self._optional_value("raycom_invoice_number", row.get("raycom_invoice_number")),
            "raycom_order_number": network_deal_number,
            "schedule": schedule.id,
            "spot_rate": spot_rate,
            "status": status,
            "time_period": self._optional_value("time_period", row.get("time_period")),
            "x800": self._optional_value("x800", row.get("x800")),
        }
        return spot_vals, False

    def _match_schedule(self, *, network, network_deal_number, air_date, air_time, length, spot_rate, import_week):
        if not self.program:
            return False, "Program is required."
        if not network_deal_number:
            return False, "Missing network deal number."

        deals = self.env["mv.deal"].search(
            [
                ("network_deal_number", "=", network_deal_number),
                ("status", "=", "sold"),
            ],
            order="id",
        )
        if not deals:
            return False, "No deal matched network deal number %s." % network_deal_number

        air_dt = build_air_datetime(air_date, air_time, parse_clock_start_number(self.program.clock_start_time))
        if not air_dt:
            return False, "Could not parse Air Date/Air Time."

        errors = []
        for deal in deals:
            start_number = parse_clock_start_number(deal.program.clock_start_time)
            if not network_name_matches(network, deal.program.name):
                errors.append("Program/network name did not match the uploaded Network value.")
                continue

            schedules = self.env["mv.schedules"].search(
                [
                    ("deal_parent", "=", deal.id),
                    ("status", "=", "sold"),
                ],
                order="id",
            )
            for schedule in schedules:
                schedule_length = schedule.unitlength or getattr(schedule.deal_parent, "length", False)
                if not length_matches(length, schedule_length):
                    errors.append("Unit length did not match the schedule unit length.")
                    continue
                if not schedule_allows_air_datetime(schedule, air_dt, start_number):
                    errors.append("Air date/time was outside the schedule day/time window.")
                    continue
                if not rate_matches(spot_rate, schedule.rate):
                    errors.append("Spot rate did not match the schedule rate.")
                    continue
                return schedule, False

        return False, errors[-1] if errors else "No schedule matched the Apex postlog rules."

    def _first_data_row_number(self):
        return int(self.config.get("headerRow", 1)) + 1
