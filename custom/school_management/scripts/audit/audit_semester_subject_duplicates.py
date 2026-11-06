"""Report duplicate semester-subject offerings without modifying data.

Usage:
    python custom/school_management/scripts/audit_semester_subject_duplicates.py \
        --config odoo.conf --database DATABASE_NAME
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

import odoo
from odoo import api
from odoo.modules.registry import Registry
from odoo.tools import config


def main():
    parser = argparse.ArgumentParser(
        description="Audit duplicate university.semester.subject pairs, including archived offerings."
    )
    parser.add_argument("--config", default=str(ROOT / "odoo.conf"))
    parser.add_argument("--database", required=True)
    args = parser.parse_args()

    config.parse_config(["-c", args.config, "--no-http", "--max-cron-threads=0"])
    registry = Registry(args.database)
    with registry.cursor() as cr:
        env = api.Environment(cr, odoo.SUPERUSER_ID, {})
        env.cr.execute(
            """
            SELECT offering.semester_id,
                   semester.name,
                   offering.subject_id,
                   subject.code,
                   subject.name,
                   array_agg(offering.id ORDER BY offering.id),
                   array_agg(offering.active ORDER BY offering.id)
              FROM university_semester_subject AS offering
              JOIN university_semester AS semester ON semester.id = offering.semester_id
              JOIN university_subject AS subject ON subject.id = offering.subject_id
             GROUP BY offering.semester_id, semester.name,
                      offering.subject_id, subject.code, subject.name
            HAVING COUNT(*) > 1
             ORDER BY semester.name, subject.name, offering.semester_id, offering.subject_id
            """
        )
        duplicates = env.cr.fetchall()
        if not duplicates:
            print("No duplicate semester-subject offerings found, including archived records.")
            return 0

        print("Duplicate semester-subject offerings found; no data was changed:")
        for semester_id, semester_name, subject_id, subject_code, subject_name, ids, active_values in duplicates:
            print(
                "  semester_id=%s (%s), subject_id=%s (%s - %s), offering_ids=%s, active=%s"
                % (
                    semester_id,
                    semester_name,
                    subject_id,
                    subject_code or "no code",
                    subject_name,
                    ids,
                    active_values,
                )
            )
        print(
            "Reconcile each pair before upgrade: select one canonical offering, reassign or preserve any external references, then archive/delete only after reference review."
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
