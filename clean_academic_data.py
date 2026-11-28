import math
import odoo
from odoo.tools import config
from odoo import api, SUPERUSER_ID
from odoo.modules.registry import Registry

def merge_records(env, cr, model_name, old_id, new_id, skip_models=None):
    """
    Generic merge helper that finds every stored Many2one to model_name via ir.model.fields,
    repoints references from old_id to new_id, and sets active=False on old_id.
    """
    skip_models = skip_models or []
    fields = env['ir.model.fields'].search([
        ('relation', '=', model_name),
        ('ttype', '=', 'many2one'),
        ('store', '=', True),
    ])
    repointed_counts = {}
    for f in fields:
        if f.model in skip_models:
            continue
        if f.model not in env:
            continue
        model_obj = env[f.model]
        table = model_obj._table
        col = f.name
        # Count matching rows
        cr.execute(f'SELECT COUNT(*) FROM "{table}" WHERE "{col}" = %s', [old_id])
        cnt = cr.fetchone()[0]
        if cnt > 0:
            cr.execute(f'UPDATE "{table}" SET "{col}" = %s WHERE "{col}" = %s', [new_id, old_id])
            repointed_counts[f"{f.model}.{f.name}"] = cnt
            print(f"  Repointed {cnt} records in {f.model}.{f.name} ({old_id} -> {new_id})")

    # Set active=False on old record if it has an active column
    old_table = env[model_name]._table
    cr.execute(f"""
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = %s AND column_name = 'active'
    """, [old_table])
    if cr.fetchone():
        cr.execute(f'UPDATE "{old_table}" SET "active" = FALSE WHERE "id" = %s', [old_id])
        print(f"  Archived {model_name} id={old_id} (active=False)")
    return repointed_counts

def run_cleanup():
    config.parse_config(['-c', 'odoo.conf', '-d', 'odoo'])
    reg = Registry.new('odoo')
    with reg.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        print("================== START ACADEMIC DATA CLEANUP ==================")
        
        # 1. Clean up old department terms first so they don't block date changes
        print("\n--- Cleaning up Department Terms ---")
        cr.execute('SELECT id FROM university_department_term')
        old_term_ids = [r[0] for r in cr.fetchall()]
        print(f"  Found {len(old_term_ids)} existing department terms: {old_term_ids}")
        if old_term_ids:
            # Check if referenced
            dept_term_fields = env['ir.model.fields'].search([
                ('relation', '=', 'university.department.term'),
                ('ttype', '=', 'many2one'),
                ('store', '=', True)
            ])
            has_ref = False
            for f in dept_term_fields:
                if f.model in env:
                    cr.execute(f'SELECT COUNT(*) FROM "{env[f.model]._table}" WHERE "{f.name}" = ANY(%s)', [old_term_ids])
                    if cr.fetchone()[0] > 0:
                        has_ref = True
                        break
            if not has_ref:
                # Delete mail messages and records safely
                cr.execute("DELETE FROM mail_message WHERE model = 'university.department.term'")
                cr.execute("DELETE FROM mail_followers WHERE res_model = 'university.department.term'")
                cr.execute("DELETE FROM university_department_term WHERE id = ANY(%s)", [old_term_ids])
                print(f"  [OK] Deleted {len(old_term_ids)} outdated department terms (0 references found)")

        # 2. Standardize Academic Year 1 (2025-2026)
        print("\n--- Standardizing Academic Year 1 ---")
        cr.execute("""
            UPDATE university_academic_year
            SET name = '2025-2026',
                date_start = '2025-09-01',
                date_end = '2026-06-30',
                state = 'running',
                current = TRUE,
                active = TRUE
            WHERE id = 1
        """)
        print("  [OK] Academic Year 1 updated to 2025-09-01 -> 2026-06-30 (running, current)")

        # 3. Standardize Semesters 2 and 3
        print("\n--- Standardizing Semesters 2 and 3 ---")
        cr.execute("""
            UPDATE university_semester
            SET name = 'Semester 1',
                academic_year_id = 1,
                session_id = 1,
                semester_type = 'semester_1',
                date_start = '2025-09-01',
                date_end = '2025-12-21',
                week_count = 16,
                active = TRUE
            WHERE id = 2
        """)
        print("  [OK] Semester 2 (Semester 1) updated to 2025-09-01 -> 2025-12-21 (16 weeks)")

        cr.execute("""
            UPDATE university_semester
            SET name = 'Semester 2',
                academic_year_id = 1,
                session_id = 1,
                semester_type = 'semester_2',
                date_start = '2026-01-05',
                date_end = '2026-04-26',
                week_count = 16,
                active = TRUE
            WHERE id = 3
        """)
        print("  [OK] Semester 3 (Semester 2) updated to 2026-01-05 -> 2026-04-26 (16 weeks)")

        # 4. Merge duplicate semesters into Semester 2 and Semester 3
        print("\n--- Merging duplicate semesters ---")
        sem_merge_map = {
            13: 2,   # Semester 1 duplicate
            1164: 2, # Year1 duplicate
            2988: 3, # Semester 2 duplicate
            1: 2,    # Full Semester (archive, point active refs to Sem 1)
        }
        for old_sid, new_sid in sem_merge_map.items():
            merge_records(env, cr, 'university.semester', old_sid, new_sid)

        # 5. Merge Academic Year 22 -> 1
        print("\n--- Merging Academic Year 22 -> 1 ---")
        # Do not repoint university.semester for year 22, as those duplicate semesters are already merged/archived
        merge_records(env, cr, 'university.academic.year', 22, 1, skip_models=['university.semester'])

        # 6. Regenerate Department Terms for Semester 1 and Semester 2
        print("\n--- Regenerating Department Terms ---")
        cr.execute("SELECT id FROM university_department WHERE active = TRUE")
        active_dept_ids = [r[0] for r in cr.fetchall()]
        print(f"  Active departments count: {len(active_dept_ids)}")
        for sid, start_d, end_d in [(2, '2025-09-01', '2025-12-21'), (3, '2026-01-05', '2026-04-26')]:
            for did in active_dept_ids:
                cr.execute("""
                    SELECT id FROM university_department_term
                    WHERE semester_id = %s AND department_id = %s
                """, [sid, did])
                if not cr.fetchone():
                    cr.execute("""
                        INSERT INTO university_department_term (
                            semester_id, department_id, date_start, date_end, teaching_weeks, state, create_uid, create_date, write_uid, write_date
                        ) VALUES (
                            %s, %s, %s, %s, 16.0, 'planned', 1, NOW(), 1, NOW()
                        )
                    """, [sid, did, start_d, end_d])
        cr.execute("SELECT COUNT(*) FROM university_department_term")
        print(f"  [OK] Total Department Terms now: {cr.fetchone()[0]}")

        # 7. Update Settings
        print("\n--- Updating Settings Parameters ---")
        ICP = env['ir.config_parameter'].sudo()
        ICP.set_param('school_management.current_academic_year_id', 1)
        ICP.set_param('school_management.current_semester_id', 2)
        ICP.set_param('school_management.min_teaching_weeks', '14')
        print("  current_academic_year_id -> 1")
        print("  current_semester_id -> 2")
        print("  min_teaching_weeks -> 14")

        # 8. Commit and invalidate
        cr.commit()
        env.invalidate_all()
        print("\n================== CLEANUP COMPLETED AND COMMITTED ==================")

if __name__ == '__main__':
    run_cleanup()
