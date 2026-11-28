"""One-off maintenance script to fix empty teacher_id on university.assignment records.

Usage:
    python custom/school_management/scripts/fix_empty_assignment_teachers.py -c odoo.conf -d <database_name>
"""
import os
import sys

# Ensure Odoo root directory is on sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import argparse
import odoo
from odoo.modules.registry import Registry
from odoo import api, SUPERUSER_ID


def fix_empty_assignment_teachers(database_name, config_file="odoo.conf"):
    print(f"Connecting to database '{database_name}' using config '{config_file}'...")
    odoo.tools.config.parse_config(["-c", config_file, "-d", database_name])
    registry = Registry(database_name)

    fixed_records = []
    unfixable_records = []

    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        Assignment = env["university.assignment"].sudo()

        # Find assignments with empty or False teacher_id via ORM or SQL
        cr.execute("SELECT id FROM university_assignment WHERE teacher_id IS NULL")
        missing_ids = [row[0] for row in cr.fetchall()]

        # Also check via ORM in case of any in-memory or soft states
        orm_missing = Assignment.search([("teacher_id", "=", False)]).ids
        all_candidate_ids = list(set(missing_ids + orm_missing))

        print(f"Found {len(all_candidate_ids)} assignment record(s) with missing teacher_id.")

        if not all_candidate_ids:
            print("No assignments require fixing. All existing records have valid teacher_id.")
            return

        assignments = Assignment.browse(all_candidate_ids)
        for assignment in assignments:
            section = assignment.section_id
            if section and section.teacher_id:
                new_teacher = section.teacher_id
                assignment.write({"teacher_id": new_teacher.id})
                fixed_records.append({
                    "id": assignment.id,
                    "name": assignment.name,
                    "section": section.name,
                    "assigned_teacher": new_teacher.name,
                })
            else:
                reason = "No linked section" if not section else f"Section '{section.name}' has no teacher assigned"
                unfixable_records.append({
                    "id": assignment.id,
                    "name": assignment.name,
                    "reason": reason,
                })

        cr.commit()

    print("\n--- Summary ---")
    print(f"Successfully fixed: {len(fixed_records)}")
    for item in fixed_records:
        print(f"  [FIXED] ID {item['id']}: '{item['name']}' -> Teacher: {item['assigned_teacher']} (from Section: {item['section']})")

    print(f"Cannot fix: {len(unfixable_records)}")
    for item in unfixable_records:
        print(f"  [UNFIXED] ID {item['id']}: '{item['name']}' -> Reason: {item['reason']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fix empty teacher_id on assignments from class section.")
    parser.add_argument("-c", "--config", default="odoo.conf", help="Path to Odoo configuration file")
    parser.add_argument("-d", "--database", default="odoo", help="Target database name")
    args = parser.parse_args()

    fix_empty_assignment_teachers(args.database, args.config)
