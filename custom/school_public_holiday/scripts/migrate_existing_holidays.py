"""One-off data backfill and normalization script for university.holiday records.

Moves existing university.holiday rows into the single source of truth model,
normalizes dates, scopes, types, and pay rates without duplicates, and logs
any records that could not be migrated. Does NOT delete anything automatically.

Usage (Odoo shell):
    python odoo-bin shell -c odoo.conf -d <dbname> < custom/school_public_holiday/scripts/migrate_existing_holidays.py
"""
import logging

_logger = logging.getLogger("migrate_existing_holidays")


def migrate_holidays(env):
    Holiday = env["university.holiday"].with_context(active_test=False)
    all_holidays = Holiday.search([])
    total_found = len(all_holidays)
    _logger.info("Found %d total university.holiday records to verify and migrate.", total_found)

    updated_count = 0
    duplicate_count = 0
    unmigrated_records = []
    seen_scopes = {}

    for h in all_holidays:
        try:
            with env.cr.savepoint():
                d_from = h.date_from or h.date_start
                d_to = h.date_to or h.date_end or d_from

                if not d_from or not d_to:
                    unmigrated_records.append({
                        "id": h.id,
                        "name": h.name,
                        "reason": "Missing start or end date",
                    })
                    continue

                if d_to < d_from:
                    unmigrated_records.append({
                        "id": h.id,
                        "name": h.name,
                        "reason": f"End date ({d_to}) is before start date ({d_from})",
                    })
                    continue

                # Scope key for duplicate detection
                key = (h.name.strip().lower(), d_from, d_to)
                if key in seen_scopes:
                    duplicate_count += 1
                    _logger.warning(
                        "Duplicate holiday detected: '%s' (ID %d) overlaps existing ID %d. Not modified.",
                        h.name, h.id, seen_scopes[key]
                    )
                    continue
                seen_scopes[key] = h.id

                vals = {}
                if not h.date_from:
                    vals["date_from"] = d_from
                if not h.date_to:
                    vals["date_to"] = d_to
                if not h.date_start:
                    vals["date_start"] = d_from
                if not h.date_end:
                    vals["date_end"] = d_to
                if not h.holiday_type:
                    vals["holiday_type"] = "public"
                if not h.work_pay_multiplier:
                    vals["work_pay_multiplier"] = 2.0

                if not h.applies_to:
                    if h.faculty_id:
                        vals["applies_to"] = "faculty"
                        if h.faculty_id not in h.faculty_ids:
                            vals["faculty_ids"] = [(4, h.faculty_id.id)]
                    else:
                        vals["applies_to"] = "all"
                elif h.applies_to == "faculty" and h.faculty_id and h.faculty_id not in h.faculty_ids:
                    vals["faculty_ids"] = [(4, h.faculty_id.id)]

                if vals:
                    h.write(vals)
                    updated_count += 1

        except Exception as exc:
            _logger.exception("Failed to migrate university.holiday ID %d: %s", h.id, str(exc))
            unmigrated_records.append({
                "id": h.id,
                "name": h.name,
                "reason": str(exc),
            })

    print("=" * 60)
    print("MIGRATION SUMMARY:")
    print(f"• Total Holidays Found: {total_found}")
    print(f"• Successfully Normalized: {updated_count}")
    print(f"• Duplicates Flagged: {duplicate_count}")
    print(f"• Unmigrated / Failed: {len(unmigrated_records)}")
    if unmigrated_records:
        print("\nUNMIGRATED RECORDS LOG:")
        for r in unmigrated_records:
            print(f"  - ID {r['id']} ({r['name']}): {r['reason']}")
    print("=" * 60)


if __name__ == "__main__" or "env" in locals():
    if "env" in locals():
        migrate_holidays(env)
    else:
        print("Please run this script inside odoo-bin shell:")
        print("python odoo-bin shell -c odoo.conf -d <dbname> < custom/school_public_holiday/scripts/migrate_existing_holidays.py")
