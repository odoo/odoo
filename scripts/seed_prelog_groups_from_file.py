#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
import re
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
import sys

import xlrd

ROOT = Path("/Users/adrianpichardo/Documents/Odoo/odoo")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import odoo
import odoo.modules.registry
import odoo.service.server
from odoo import SUPERUSER_ID, api


CONF_PATH = str(ROOT / "odoo.conf")
DAY_CODE_BY_WEEKDAY = {
    0: "Mon",
    1: "Tue",
    2: "Wed",
    3: "Thu",
    4: "Fri",
    5: "Sat",
    6: "Sun",
}


def parse_args():
    parser = argparse.ArgumentParser(description="Seed deals and schedules from a Prelog upload file.")
    parser.add_argument("--db", default="odoo_tcn_prod_copy")
    parser.add_argument("--program-name", default="True Crime Network")
    parser.add_argument(
        "--file",
        default="/Users/adrianpichardo/Downloads/True Crime Network Prelog 6.29 V5.xls",
    )
    parser.add_argument("--network", default="true_crime_network")
    return parser.parse_args()


def parse_workbook_rows(path: Path):
    book = xlrd.open_workbook(path)
    sheet = book.sheet_by_index(0)
    header = [str(value).strip() if value is not None else "" for value in sheet.row_values(0)]
    rows = []
    for row_index in range(1, sheet.nrows):
        values = sheet.row_values(row_index)
        row = {key: (values[idx] if idx < len(values) else "") for idx, key in enumerate(header)}
        if is_non_data_row(row):
            continue
        rows.append(row)
    return rows


def is_non_data_row(row):
    return not any(
        normalize_text(row.get(field))
        for field in ("Air Date", "Sched Time", "Deal/Order #", "Program", "Agency", "Advertiser/Product")
    )


def normalize_text(value):
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def parse_airdate(value):
    text = normalize_text(value)
    return datetime.strptime(text, "%m/%d/%y").date()


def parse_rate(value):
    text = normalize_text(value)
    return float(text)


def parse_length_seconds(value):
    text = normalize_text(value)
    if not text:
        raise ValueError("Missing schedule length.")
    parts = text.split(":")
    if len(parts) == 2:
        minutes_text, seconds_text = parts
        minutes = int(minutes_text or 0)
        seconds = int(seconds_text or 0)
        return minutes * 60 + seconds
    if len(parts) == 3:
        hours, minutes, seconds = (int(part or 0) for part in parts)
        return hours * 3600 + minutes * 60 + seconds
    return int(float(text))


def monday_of(value: date):
    return value - timedelta(days=value.weekday())


def parse_daypart_window(value):
    text = normalize_text(value).upper()
    if not text:
        raise ValueError("Missing daypart.")
    text = text.strip("()").replace(" TO ", "-").replace("XM", "AM")
    match = re.match(
        r"^(\d{1,2})(?::(\d{2}))?\s*([AP](?:M)?)\s*-\s*(\d{1,2})(?::(\d{2}))?\s*([AP](?:M)?)$",
        text,
    )
    if not match:
        raise ValueError(f"Unsupported daypart format: {value}")
    return (
        build_odoo_time_label(match.group(1), match.group(2), match.group(3)),
        build_odoo_time_label(match.group(4), match.group(5), match.group(6)),
    )


def build_odoo_time_label(hour_text, minute_text, suffix_text):
    hour = int(hour_text)
    minute = int(minute_text or "00")
    suffix = "A" if suffix_text.startswith("A") else "P"
    return f"{hour:02d}:{minute:02d}{suffix}"


def reverse_selection_map(field):
    selection = field.selection
    if callable(selection):
        selection = selection()
    return {label: key for key, label in selection}


def length_selection_key(length_seconds, label_to_key):
    label = str(int(length_seconds))
    key = label_to_key.get(label)
    if not key:
        raise ValueError(f"No deal length selection found for {length_seconds} seconds.")
    return key


def group_rows(rows):
    groups = defaultdict(list)
    for row in rows:
        deal_number = normalize_text(row.get("Deal/Order #"))
        groups[deal_number].append(row)
    return groups


def schedule_groups(rows):
    grouped = defaultdict(list)
    for row in rows:
        airdate = parse_airdate(row["Air Date"])
        week = monday_of(airdate)
        rate = parse_rate(row["Rate"])
        daypart = normalize_text(row["Time Period"])
        grouped[(week, rate, daypart)].append(row)
    return grouped


def main():
    args = parse_args()
    file_path = Path(args.file)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    odoo.tools.config.parse_config(["-c", CONF_PATH, "-d", args.db])
    odoo.service.server.load_server_wide_modules()
    registry = odoo.modules.registry.Registry(args.db)

    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})

        program = env["mv.programs"].search([("name", "ilike", args.program_name)], limit=1)
        if not program:
            raise RuntimeError(f"Program '{args.program_name}' was not found.")

        program.write({"clock_start_time": "v_6am"})

        day_tags = {
            tag.code: tag.id
            for tag in env["mv.days_allowed.tag"].search([("code", "in", list(DAY_CODE_BY_WEEKDAY.values()))])
        }
        deal_length_by_label = reverse_selection_map(env["mv.deal"]._fields["length"])
        schedule_time_by_label = reverse_selection_map(env["mv.schedules"]._fields["start_time"])

        rows = parse_workbook_rows(file_path)
        deals_by_number = group_rows(rows)

        created_deals = 0
        updated_deals = 0
        created_schedules = 0
        updated_schedules = 0

        for deal_number, deal_rows in deals_by_number.items():
            first_row = deal_rows[0]
            first_airdate = parse_airdate(first_row["Air Date"])
            length_seconds = parse_length_seconds(first_row["Sched Length"])
            deal_vals = {
                "program": program.id,
                "network_deal_number": deal_number,
                "status": "sold",
                "length": length_selection_key(length_seconds, deal_length_by_label),
                "year": first_airdate.year,
                "quarter": f"q{((first_airdate.month - 1) // 3) + 1}",
                "rate": parse_rate(first_row["Rate"]),
            }

            deal = env["mv.deal"].search(
                [("program", "=", program.id), ("network_deal_number", "=", deal_number)],
                limit=1,
            )
            if deal:
                deal.write(deal_vals)
                updated_deals += 1
            else:
                deal = env["mv.deal"].create(deal_vals)
                created_deals += 1

            for (week, rate, daypart), schedule_rows_for_group in schedule_groups(deal_rows).items():
                start_label, end_label = parse_daypart_window(daypart)
                start_key = schedule_time_by_label.get(start_label)
                end_key = schedule_time_by_label.get(end_label)
                if not start_key or not end_key:
                    raise ValueError(f"Could not map daypart '{daypart}' to Odoo schedule times.")

                day_ids = sorted(
                    {
                        day_tags[DAY_CODE_BY_WEEKDAY[parse_airdate(row["Air Date"]).weekday()]]
                        for row in schedule_rows_for_group
                    }
                )
                comments = normalize_text(schedule_rows_for_group[0].get("Program")) or deal_number
                marker = f"seed:prelog:{file_path.name}:{deal_number}:{week.isoformat()}:{rate}:{daypart}"
                schedule_vals = {
                    "sf_external_id": marker,
                    "deal_parent": deal.id,
                    "week": week,
                    "status": "sold",
                    "rate": rate,
                    "start_time": start_key,
                    "end_time": end_key,
                    "days_allowed": [(6, 0, day_ids)],
                    "comments": comments,
                    "networks": args.network,
                }

                schedule = env["mv.schedules"].search([("sf_external_id", "=", marker)], limit=1)
                if not schedule:
                    schedule = env["mv.schedules"].search(
                        [
                            ("deal_parent", "=", deal.id),
                            ("week", "=", week),
                            ("rate", "=", rate),
                            ("start_time", "=", start_key),
                            ("end_time", "=", end_key),
                        ],
                        limit=1,
                    )

                if schedule:
                    schedule.write(schedule_vals)
                    updated_schedules += 1
                else:
                    env["mv.schedules"].create(schedule_vals)
                    created_schedules += 1

        cr.commit()
        print(
            "Seed complete. "
            f"Deals created={created_deals}, deals updated={updated_deals}, "
            f"schedules created={created_schedules}, schedules updated={updated_schedules}."
        )


if __name__ == "__main__":
    main()
