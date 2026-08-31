#!/usr/bin/env python3

from datetime import date
from pathlib import Path
import sys

ROOT = Path("/Users/adrianpichardo/Documents/Odoo/odoo")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import odoo
import odoo.modules.registry
import odoo.service.server
from odoo import SUPERUSER_ID, api


CONF_PATH = "/Users/adrianpichardo/Documents/Odoo/odoo/odoo.conf"
DB_NAME = "odoo_dev"
PROGRAM_NAME = "true crime network"
WEEK_START = date(2026, 7, 6)

ROWS = [
    {
        "network_deal_number": "24481",
        "airdate": date(2026, 7, 9),
        "rate": 185,
        "length_seconds": 180,
        "program_title": "NEW DETECTIVES",
    },
    {
        "network_deal_number": "24586",
        "airdate": date(2026, 7, 9),
        "rate": 16,
        "length_seconds": 15,
        "program_title": "NEW DETECTIVES",
    },
    {
        "network_deal_number": "24588",
        "airdate": date(2026, 7, 9),
        "rate": 16,
        "length_seconds": 15,
        "program_title": "NEW DETECTIVES",
    },
    {
        "network_deal_number": "24579",
        "airdate": date(2026, 7, 9),
        "rate": 60,
        "length_seconds": 60,
        "program_title": "NEW DETECTIVES",
    },
    {
        "network_deal_number": "24661",
        "airdate": date(2026, 7, 10),
        "rate": 75,
        "length_seconds": 60,
        "program_title": "NEW DETECTIVES",
    },
    {
        "network_deal_number": "24377",
        "airdate": date(2026, 7, 11),
        "rate": 70,
        "length_seconds": 60,
        "program_title": "NEW DETECTIVES",
    },
]

DEAL_LENGTH_SELECTION = {
    15: "v_15",
    60: "v_60",
    180: "v_180",
}

DAY_CODE_BY_WEEKDAY = {
    0: "Mon",
    1: "Tue",
    2: "Wed",
    3: "Thu",
    4: "Fri",
    5: "Sat",
    6: "Sun",
}


def main():
    odoo.tools.config.parse_config(["-c", CONF_PATH, "-d", DB_NAME])
    odoo.service.server.load_server_wide_modules()
    registry = odoo.modules.registry.Registry(DB_NAME)
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})

        program = env["mv.programs"].search([("name", "=", PROGRAM_NAME)], limit=1)
        if not program:
            raise RuntimeError(f"Program '{PROGRAM_NAME}' was not found.")

        program.write({"clock_start_time": "v_6am"})

        day_tags = {
            rec.code: rec
            for rec in env["mv.days_allowed.tag"].search([("code", "in", list(DAY_CODE_BY_WEEKDAY.values()))])
        }

        created_deals = 0
        updated_deals = 0
        created_schedules = 0
        updated_schedules = 0

        for row in ROWS:
            deal_length = DEAL_LENGTH_SELECTION[row["length_seconds"]]
            day_code = DAY_CODE_BY_WEEKDAY[row["airdate"].weekday()]
            day_tag = day_tags[day_code]

            deal = env["mv.deal"].search(
                [
                    ("program", "=", program.id),
                    ("network_deal_number", "=", row["network_deal_number"]),
                ],
                limit=1,
            )

            deal_vals = {
                "program": program.id,
                "network_deal_number": row["network_deal_number"],
                "status": "sold",
                "length": deal_length,
                "year": row["airdate"].year,
                "quarter": "q3",
                "rate": row["rate"],
            }

            if deal:
                deal.write(deal_vals)
                updated_deals += 1
            else:
                deal = env["mv.deal"].create(deal_vals)
                created_deals += 1

            schedule = env["mv.schedules"].search(
                [
                    ("deal_parent", "=", deal.id),
                    ("week", "=", WEEK_START),
                    ("status", "=", "sold"),
                    ("rate", "=", row["rate"]),
                ],
                limit=1,
            )

            schedule_vals = {
                "deal_parent": deal.id,
                "week": WEEK_START,
                "status": "sold",
                "rate": row["rate"],
                "start_time": "v_06_00a",
                "end_time": "v_09_00a",
                "days_allowed": [(6, 0, [day_tag.id])],
                "day": row["airdate"],
                "comments": row["program_title"],
                "networks": "true_crime_network",
            }

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
