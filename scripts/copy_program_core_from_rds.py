#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
from collections import defaultdict
from pathlib import Path
import sys

import psycopg2
import psycopg2.extras

ROOT = Path("/Users/adrianpichardo/Documents/Odoo/odoo")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import odoo
import odoo.modules.registry
import odoo.service.server
from odoo import SUPERUSER_ID, api


CONF_PATH = str(ROOT / "odoo.conf")
REMOTE_KEY_PREFIX = "rds"


def parse_args():
    parser = argparse.ArgumentParser(description="Copy one program's core data from remote RDS into a local Odoo DB.")
    parser.add_argument("--local-db", default="odoo_tcn_prod_copy")
    parser.add_argument("--remote-host", default=os.environ.get("REMOTE_PGHOST"))
    parser.add_argument("--remote-port", type=int, default=int(os.environ.get("REMOTE_PGPORT", "5432")))
    parser.add_argument("--remote-db", default=os.environ.get("REMOTE_PGDATABASE", "mydb"))
    parser.add_argument("--remote-user", default=os.environ.get("REMOTE_PGUSER"))
    parser.add_argument("--remote-password", default=os.environ.get("REMOTE_PGPASSWORD"))
    parser.add_argument("--program-name", default="True Crime Network")
    return parser.parse_args()


def remote_key(table_name: str, record_id: int) -> str:
    return f"{REMOTE_KEY_PREFIX}:{table_name}:{record_id}"


def connect_remote(args):
    missing = [name for name, value in {
        "remote-host": args.remote_host,
        "remote-user": args.remote_user,
        "remote-password": args.remote_password,
        "remote-db": args.remote_db,
    }.items() if not value]
    if missing:
        raise RuntimeError(f"Missing remote connection values: {', '.join(missing)}")
    return psycopg2.connect(
        host=args.remote_host,
        port=args.remote_port,
        dbname=args.remote_db,
        user=args.remote_user,
        password=args.remote_password,
    )


def fetch_remote_program(cur, program_name):
    cur.execute(
        """
        select id, name, clientcode, clock_start_time, prelog_version
        from mv_programs
        where lower(name) = lower(%s)
        order by id
        limit 1
        """,
        (program_name,),
    )
    program = cur.fetchone()
    if not program:
        raise RuntimeError(f"Remote program '{program_name}' was not found.")
    return program


def fetch_remote_deals(cur, remote_program_id):
    cur.execute(
        """
        select id, name, network_deal_number, status, length, rate, year, quarter
        from mv_deal
        where program = %s
        order by id
        """,
        (remote_program_id,),
    )
    return cur.fetchall()


def fetch_remote_schedules(cur, remote_program_id):
    cur.execute(
        """
        select s.id, s.deal_parent, s.week, s.status, s.rate, s.start_time, s.end_time, s.day, s.comments, s.networks
        from mv_schedules s
        join mv_deal d on d.id = s.deal_parent
        where d.program = %s
        order by s.id
        """,
        (remote_program_id,),
    )
    return cur.fetchall()


def fetch_remote_schedule_day_codes(cur, remote_program_id):
    cur.execute(
        """
        select rel.mv_schedules_id, tag.code
        from mv_schedules_days_allowed_rel rel
        join mv_days_allowed_tag tag on tag.id = rel.mv_days_allowed_tag_id
        where rel.mv_schedules_id in (
            select s.id
            from mv_schedules s
            join mv_deal d on d.id = s.deal_parent
            where d.program = %s
        )
        order by rel.mv_schedules_id, tag.code
        """,
        (remote_program_id,),
    )
    codes_by_schedule = defaultdict(list)
    for row in cur.fetchall():
        codes_by_schedule[row["mv_schedules_id"]].append(row["code"])
    return codes_by_schedule


def build_local_env(local_db):
    os.chdir(ROOT)
    odoo.tools.config.parse_config(["-c", CONF_PATH, "-d", local_db])
    odoo.service.server.load_server_wide_modules()
    registry = odoo.modules.registry.Registry(local_db)
    cr = registry.cursor()
    env = api.Environment(cr, SUPERUSER_ID, {})
    return cr, env


def upsert_program(env, remote_program):
    Program = env["mv.programs"]
    marker = remote_key("mv_programs", remote_program["id"])
    program = Program.search([("sf_external_id", "=", marker)], limit=1)
    if not program:
        program = Program.search([("name", "=", remote_program["name"])], limit=1)

    vals = {
        "sf_external_id": marker,
        "name": remote_program["name"],
        "clientcode": remote_program["clientcode"],
        "clock_start_time": remote_program["clock_start_time"] or False,
        "prelog_version": remote_program["prelog_version"] or 0,
    }
    if program:
        program.write(vals)
        created = False
    else:
        program = Program.create(vals)
        created = True
    return program, created


def upsert_deals(env, remote_deals, local_program):
    Deal = env["mv.deal"]
    deal_id_map = {}
    created = 0
    updated = 0
    for remote_deal in remote_deals:
        marker = remote_key("mv_deal", remote_deal["id"])
        deal = Deal.search([("sf_external_id", "=", marker)], limit=1)
        vals = {
            "sf_external_id": marker,
            "program": local_program.id,
            "network_deal_number": remote_deal["network_deal_number"],
            "status": remote_deal["status"] or "sold",
            "length": remote_deal["length"] or False,
            "rate": remote_deal["rate"] or 0,
            "year": remote_deal["year"] or False,
            "quarter": remote_deal["quarter"] or False,
        }
        if deal:
            deal.write(vals)
            updated += 1
        else:
            deal = Deal.create(vals)
            updated += 0
            created += 1
        deal_id_map[remote_deal["id"]] = deal.id
    return deal_id_map, created, updated


def upsert_schedules(env, remote_schedules, schedule_day_codes, local_deal_id_map):
    Schedule = env["mv.schedules"]
    day_tag_by_code = {
        tag.code: tag.id
        for tag in env["mv.days_allowed.tag"].search([])
        if tag.code
    }

    created = 0
    updated = 0
    for remote_schedule in remote_schedules:
        marker = remote_key("mv_schedules", remote_schedule["id"])
        schedule = Schedule.search([("sf_external_id", "=", marker)], limit=1)
        local_deal_id = local_deal_id_map[remote_schedule["deal_parent"]]

        local_day_ids = [
            day_tag_by_code[code]
            for code in schedule_day_codes.get(remote_schedule["id"], [])
            if code in day_tag_by_code
        ]

        vals = {
            "sf_external_id": marker,
            "deal_parent": local_deal_id,
            "week": remote_schedule["week"],
            "status": remote_schedule["status"] or "sold",
            "rate": remote_schedule["rate"] or 0,
            "start_time": remote_schedule["start_time"] or False,
            "end_time": remote_schedule["end_time"] or False,
            "day": remote_schedule["day"] or False,
            "comments": remote_schedule["comments"] or False,
            "networks": remote_schedule["networks"] or False,
            "days_allowed": [(6, 0, local_day_ids)],
        }
        if schedule:
            schedule.write(vals)
            updated += 1
        else:
            Schedule.create(vals)
            created += 1
    return created, updated


def main():
    args = parse_args()
    remote_conn = connect_remote(args)
    remote_cur = remote_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    remote_program = fetch_remote_program(remote_cur, args.program_name)
    remote_deals = fetch_remote_deals(remote_cur, remote_program["id"])
    remote_schedules = fetch_remote_schedules(remote_cur, remote_program["id"])
    schedule_day_codes = fetch_remote_schedule_day_codes(remote_cur, remote_program["id"])

    local_cr, env = build_local_env(args.local_db)
    try:
        local_program, program_created = upsert_program(env, remote_program)
        local_deal_id_map, deals_created, deals_updated = upsert_deals(env, remote_deals, local_program)
        schedules_created, schedules_updated = upsert_schedules(env, remote_schedules, schedule_day_codes, local_deal_id_map)
        local_cr.commit()
    finally:
        local_cr.close()
        remote_cur.close()
        remote_conn.close()

    print(
        "Copy complete. "
        f"Program created={int(program_created)}. "
        f"Deals created={deals_created}, deals updated={deals_updated}. "
        f"Schedules created={schedules_created}, schedules updated={schedules_updated}."
    )


if __name__ == "__main__":
    main()
