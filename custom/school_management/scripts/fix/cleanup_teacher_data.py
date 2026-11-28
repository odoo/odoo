"""Safe and reversible data audit & cleanup script for university.teacher records.

Usage:
    # 1. Audit / dry-run (lists issues, makes no changes):
    python custom/school_management/scripts/cleanup_teacher_data.py --dry-run

    # 2. Apply fixes (after reviewing audit results):
    python custom/school_management/scripts/cleanup_teacher_data.py --apply
"""

import argparse
import re
import sys

sys.path.insert(0, r"C:\Odoo\odoo")
import odoo
from odoo.tools import config

TITLES_MAP = {
    "dr.": "dr",
    "dr": "dr",
    "prof.": "prof",
    "prof": "prof",
    "mr.": "mr",
    "mr": "mr",
    "ms.": "ms",
    "ms": "ms",
    "mrs.": "mrs",
    "mrs": "mrs",
}

STANDARD_ID_PATTERN = re.compile(r"^TCH-\d{4}$")
EMAIL_PATTERN = re.compile(r"^[\w\.\+\-]+@[a-zA-Z0-9\-]+(\.[a-zA-Z0-9\-]+)+$")


def run_cleanup(apply_fixes=False):
    config.parse_config(["-c", "C:/Odoo/odoo/odoo.conf"])
    registry = odoo.modules.registry.Registry("odoo")

    mode_label = "APPLYING FIXES" if apply_fixes else "DRY-RUN (AUDIT ONLY - NO CHANGES)"
    print("=" * 80)
    print(f" UNIVERSITY TEACHER / ACADEMIC STAFF DATA CLEANUP: {mode_label}")
    print("=" * 80)

    with registry.cursor() as cr:
        env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
        teachers = env["university.teacher"].with_context(active_test=False).search([])

        # -------------------------------------------------------------
        # 1. Embedded Titles & Name Normalization Audit & Fix
        # -------------------------------------------------------------
        print("\n[1] AUDIT: Embedded Titles & Lowercase Names")
        title_fixes = []
        name_fixes = []

        for t in teachers:
            raw_name = t.name or ""
            parts = raw_name.strip().split()
            if not parts:
                continue

            first_lower = parts[0].lower()
            detected_title = TITLES_MAP.get(first_lower)
            has_embedded_title = detected_title is not None
            cleaned_parts = parts[1:] if has_embedded_title else parts
            normalized_name = " ".join(part.capitalize() for part in cleaned_parts)

            needs_title_fix = has_embedded_title and (t.title != detected_title or t.name != normalized_name)
            needs_name_fix = (t.name != normalized_name)

            if needs_title_fix or needs_name_fix:
                target_title = detected_title or t.title
                title_fixes.append({
                    "record": t,
                    "old_name": t.name,
                    "old_title": t.title,
                    "new_name": normalized_name,
                    "new_title": target_title,
                })
                print(
                    f"  -> STAFF ID {t.id:3d} ({str(t.teacher_id):12s}): "
                    f"Name: {t.name!r} [Title: {t.title!r}] ==> Target: Name: {normalized_name!r} [Title: {target_title!r}]"
                )

        if not title_fixes:
            print("  -> OK: All teacher names and titles are properly formatted.")
        elif apply_fixes:
            for item in title_fixes:
                rec = item["record"]
                # Direct SQL or write bypassing create/write recursion
                vals = {"name": item["new_name"]}
                if item["new_title"]:
                    vals["title"] = item["new_title"]
                rec.write(vals)
                rec._compute_display_name()
                print(f"     [FIXED] Updated ID {rec.id}: Display Name is now {rec.display_name!r}")

        # -------------------------------------------------------------
        # 2. Staff ID Standards & Duplicates Audit
        # -------------------------------------------------------------
        print("\n[2] AUDIT: Staff IDs (Format & Uniqueness)")
        id_map = {}
        non_standard_ids = []

        for t in teachers:
            sid = (t.teacher_id or "").strip()
            if not sid:
                print(f"  -> BLANK ID: Staff ID {t.id:3d} ({t.name!r}) has no staff ID assigned.")
            else:
                id_map.setdefault(sid.lower(), []).append(t)
                if not STANDARD_ID_PATTERN.match(sid):
                    non_standard_ids.append((t, sid))

        for low_id, group in id_map.items():
            if len(group) > 1:
                print(f"  -> DUPLICATE STAFF ID (case-insensitive '{low_id}'):")
                for st in group:
                    print(f"     - ID {st.id:3d} | Name: {st.display_name or st.name!r} | Staff ID: {st.teacher_id!r} | Active: {st.active}")
                print("     [POLICY] Existing IDs are NOT overwritten without manual confirmation.")

        if non_standard_ids:
            print("  -> Non-standard Staff IDs (Standard is 'TCH-XXXX' with 4 digits):")
            for st, sid in non_standard_ids:
                print(f"     - ID {st.id:3d} | Name: {st.display_name or st.name:25s} | Current Staff ID: {sid!r}")
            print("     [POLICY] Existing IDs are preserved per requirement unless explicitly instructed to renumber.")
        else:
            print("  -> OK: All assigned staff IDs match standard format 'TCH-XXXX'.")

        # -------------------------------------------------------------
        # 3. Email Format & Uniqueness Audit
        # -------------------------------------------------------------
        print("\n[3] AUDIT: Email Format & Uniqueness")
        email_map = {}
        invalid_emails = []

        for t in teachers:
            em = (t.email or "").strip()
            if em:
                email_map.setdefault(em.lower(), []).append(t)
                if not EMAIL_PATTERN.match(em):
                    invalid_emails.append((t, em))

        for low_em, group in email_map.items():
            if len(group) > 1:
                print(f"  -> DUPLICATE EMAIL (case-insensitive '{low_em}'):")
                for st in group:
                    print(f"     - ID {st.id:3d} | Name: {st.display_name or st.name!r} | Email: {st.email!r}")

        if invalid_emails:
            print("  -> Invalid email formats:")
            for st, em in invalid_emails:
                print(f"     - ID {st.id:3d} | Name: {st.display_name or st.name!r} | Invalid Email: {em!r}")
        else:
            print("  -> OK: No duplicate or malformed emails found.")

        # -------------------------------------------------------------
        # 4. Test Data & Record Safeguards
        # -------------------------------------------------------------
        print("\n[4] AUDIT: Test / Dummy Data & Safeguards")
        dummy_candidates = teachers.filtered(
            lambda t: any(w in (t.name or "").lower() for w in ["test", "lorem", "aut porro", "deleniti"])
        )

        for d in dummy_candidates:
            sections = len(d.section_ids)
            sessions = len(d.timetable_slot_ids)
            attendances = env["university.staff.attendance"].search_count([("staff_id", "=", d.id)])
            assignments = len(d.assignment_ids)
            print(
                f"  -> CANDIDATE DUMMY RECORD: ID {d.id:3d} | Name: {d.name!r} | Staff ID: {d.teacher_id!r} | "
                f"Sections: {sections} | Sessions: {sessions} | Attendance: {attendances} | Roles: {assignments}"
            )
            has_linked = sections > 0 or sessions > 0 or attendances > 0 or assignments > 0
            if has_linked:
                print(f"     [SAFEGUARD] Teacher '{d.name}' cannot be deleted because of linked data. Must archive only.")
            else:
                print(f"     [SAFE TO ARCHIVE] Teacher '{d.name}' has no linked records and can be archived.")
                if apply_fixes and d.active:
                    d.active = False
                    print(f"     [FIXED] Archived dummy record ID {d.id} (active=False).")

        # -------------------------------------------------------------
        # 5. Summary Overview
        # -------------------------------------------------------------
        print("\n[5] CURRENT ACADEMIC STAFF OVERVIEW:")
        for t in teachers:
            sections = len(t.section_ids)
            sessions = len(t.timetable_slot_ids)
            t_dept = t.department_id.name if t.department_id else "None"
            t_fac = t.faculty_id.name if t.faculty_id else "None"
            print(
                f"     ID {t.id:3d} | {str(t.teacher_id or 'None'):12s} | {str(t.display_name or t.name):28s} | "
                f"Dept: {t_dept:30s} | Fac: {t_fac:30s} | Classes: {sections} | Active: {str(t.active):5s}"
            )

        if apply_fixes:
            cr.commit()
            print("\n>>> ALL SAFE FIXES (TITLE SPLIT, NAME NORMALIZATION) APPLIED AND COMMITTED.")
        else:
            print("\n>>> DRY-RUN AUDIT COMPLETE. No database records were modified.")
            print("    Run with '--apply' (or '--apply --confirm') to apply safe title & name fixes.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="University teacher data cleanup script.")
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
