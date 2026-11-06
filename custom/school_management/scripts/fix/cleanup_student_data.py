"""Safe and reversible data audit & cleanup script for university.student records.

Usage:
    # 1. Audit / dry-run (lists issues, makes no changes):
    python custom/school_management/scripts/cleanup_student_data.py --dry-run

    # 2. Apply fixes (after reviewing audit results):
    python custom/school_management/scripts/cleanup_student_data.py --apply
"""

import argparse
import sys

sys.path.insert(0, r"C:\Odoo\odoo")
import odoo
from odoo.tools import config


def run_cleanup(apply_fixes=False):
    config.parse_config(["-c", "C:/Odoo/odoo/odoo.conf"])
    registry = odoo.modules.registry.Registry("odoo")

    mode_label = "APPLYING FIXES" if apply_fixes else "DRY-RUN (AUDIT ONLY - NO CHANGES)"
    print("=" * 70)
    print(f" UNIVERSITY STUDENT DATA CLEANUP: {mode_label}")
    print("=" * 70)

    with registry.cursor() as cr:
        env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})

        # -------------------------------------------------------------
        # 1. Department & Faculty Mismatch Audit & Fix
        # -------------------------------------------------------------
        print("\n[1] AUDIT: Department & Faculty Misalignments")
        dept_fixes = [
            ("Department of Marketing & Logistics", "Faculty of Business Administration"),
            ("Department of Clinical Medicine", "Faculty of Medicine & Health Sciences"),
        ]

        for dept_name, target_fac_name in dept_fixes:
            dept = env["university.department"].search([("name", "=", dept_name)], limit=1)
            target_fac = env["university.faculty"].search([("name", "=", target_fac_name)], limit=1)
            if dept and target_fac:
                if dept.faculty_id.id != target_fac.id:
                    print(
                        f"  -> MISALIGNMENT: {dept.name!r} (ID {dept.id}) is linked to "
                        f"{dept.faculty_id.name!r} (ID {dept.faculty_id.id}), expected {target_fac.name!r} (ID {target_fac.id})"
                    )
                    if apply_fixes:
                        dept.faculty_id = target_fac.id
                        print(f"     [FIXED] Updated {dept.name} faculty to {target_fac.name}.")
                else:
                    print(f"  -> OK: {dept.name!r} is correctly linked to {target_fac.name!r}.")
            else:
                print(f"  -> WARNING: Could not find dept {dept_name!r} or faculty {target_fac_name!r}")

        # -------------------------------------------------------------
        # 2. Program Name Typos Audit & Fix
        # -------------------------------------------------------------
        print("\n[2] AUDIT: Program Name Typos")
        typo_prog = env["university.program"].search([("name", "=", "Accountting")], limit=1)
        if typo_prog:
            print(f"  -> TYPO FOUND: Program ID {typo_prog.id} is named {typo_prog.name!r} (code: {typo_prog.code})")
            if apply_fixes:
                typo_prog.name = "Accounting"
                print(f"     [FIXED] Renamed Program ID {typo_prog.id} to 'Accounting'.")
        else:
            print("  -> OK: No program named 'Accountting' found (already fixed or not present).")

        # -------------------------------------------------------------
        # 3. Test & Junk Data Audit & Archive (NEVER delete)
        # -------------------------------------------------------------
        print("\n[3] AUDIT: Test / Local Student Records")
        test_students = env["university.student"].with_context(active_test=False).search([
            "|", ("name", "in", ["Test", "Local"]),
            ("student_id", "in", ["std-0022", "local12"]),
        ])

        for s in test_students:
            enrollments_count = len(s.enrollment_ids)
            reports_count = len(s.report_card_ids)
            transcripts_count = len(s.transcript_ids)
            fees_count = len(s.fee_ids)
            print(
                f"  -> TEST RECORD: Student ID {s.id}, Name: {s.name!r}, Student_ID: {s.student_id!r}, "
                f"Active: {s.active}, Enrollments: {enrollments_count}, ReportCards: {reports_count}, Transcripts: {transcripts_count}, Fees: {fees_count}"
            )
            print("     [POLICY] Never delete student records with associated data. Archive (active=False) only.")
            if apply_fixes:
                if s.active:
                    s.active = False
                    print(f"     [FIXED] Archived student {s.name!r} (ID {s.id}) by setting active=False.")
                else:
                    print(f"     [ALREADY ARCHIVED] Student {s.name!r} (ID {s.id}) is already inactive.")

        # -------------------------------------------------------------
        # 4. Duplicate & Non-standard Student IDs
        # -------------------------------------------------------------
        print("\n[4] AUDIT: Duplicate & Non-standard Student IDs")
        all_students = env["university.student"].with_context(active_test=False).search([])
        id_map = {}
        for s in all_students:
            sid = (s.student_id or "").strip()
            if sid:
                id_map.setdefault(sid.lower(), []).append(s)

        for low_id, studs in id_map.items():
            if len(studs) > 1:
                print(f"  -> DUPLICATE DETECTED (case-insensitive '{low_id}'):")
                for st in studs:
                    print(f"     - ID {st.id}: Name {st.name!r}, Student ID {st.student_id!r}, Active: {st.active}")
                print("     [NOTE] Flagged for manual review / merge. IDs not overwritten without confirmation.")

        print("\n  Summary of Student ID formats in system:")
        for s in all_students:
            print(f"     - Student ID {s.id:4d} | Name: {s.name:20s} | Student_ID: {s.student_id or 'None':12s} | Status: {s.status:10s} | Active: {str(s.active):5s}")

        # -------------------------------------------------------------
        # 5. Recompute Student Faculty & Department
        # -------------------------------------------------------------
        print("\n[5] Recomputing student faculty & department derivations...")
        for s in all_students:
            old_dept = s.department_id.name if s.department_id else "None"
            old_fac = s.faculty_id.name if s.faculty_id else "None"
            if apply_fixes:
                if s.program_id:
                    s._compute_department_id()
                # Recompute faculty_id from department
                if s.department_id:
                    s.faculty_id = s.department_id.faculty_id.id
            new_dept = s.department_id.name if s.department_id else "None"
            new_fac = s.faculty_id.name if s.faculty_id else "None"
            if old_fac != new_fac:
                print(f"  -> Student {s.name} (ID {s.id}): Faculty changed '{old_fac}' -> '{new_fac}'")

        if apply_fixes:
            cr.commit()
            print("\n>>> ALL FIXES APPLIED AND COMMITTED SUCCESSFULLY.")
        else:
            print("\n>>> DRY-RUN COMPLETE. No changes were saved to the database.")
            print("    To apply these changes, run with: --apply")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="University student data cleanup script.")
    parser.add_argument("--apply", action="store_true", help="Apply fixes to database (default is dry-run)")
    parser.add_argument("--confirm", "--yes", "-y", action="store_true", dest="confirm", help="Confirm and apply fixes without prompting")
    parser.add_argument("--dry-run", action="store_true", help="Audit only without writing changes")
    args = parser.parse_args()

    if args.dry_run or not args.apply:
        run_cleanup(apply_fixes=False)
    elif args.apply and not args.confirm:
        print("Running preliminary audit before asking for confirmation...")
        run_cleanup(apply_fixes=False)
        try:
            resp = input("\nAre you sure you want to apply these database fixes? [y/N]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            resp = "n"
        if resp in ("y", "yes"):
            run_cleanup(apply_fixes=True)
        else:
            print("Aborted. No changes were made to the database.")
    else:
        run_cleanup(apply_fixes=True)
