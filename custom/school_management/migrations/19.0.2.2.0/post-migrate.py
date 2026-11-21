import datetime
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """Post-migration script to clean up academic years, semesters, department terms,
    and update settings and timeline fields idempotently.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})

    # 1. Update Academic Year 1 ("2025-2026")
    cr.execute("""
        UPDATE university_academic_year
        SET date_start = '2025-09-01',
            date_end = '2026-06-30',
            state = 'running',
            current = true,
            active = true
        WHERE id = 1;
    """)

    # 2. Merge duplicate Academic Year 22 ("2025-2026 (Standard)") into 1
    cr.execute("SELECT id FROM university_academic_year WHERE id = 22;")
    if cr.fetchone():
        # Repoint Many2one fields
        year_repoints = [
            ("university_student", "academic_year_id"),
            ("university_enrollment", "academic_year_id"),
            ("university_fee", "academic_year_id"),
            ("university_assessment_result", "academic_year_id"),
            ("university_assignment_submission", "academic_year_id"),
            ("university_timetable_slot", "academic_year_id"),
            ("university_exam", "academic_year_id"),
            ("university_class_section", "academic_year_id"),
            ("public_holiday", "academic_year_id"),
        ]
        for tbl, col in year_repoints:
            cr.execute(f"""
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = %s AND column_name = %s;
            """, (tbl, col))
            if cr.fetchone():
                cr.execute(f"UPDATE {tbl} SET {col} = 1 WHERE {col} = 22;")

        cr.execute("UPDATE university_academic_year SET active = false, current = false WHERE id = 22;")

    # 3. Standardize Semesters 2 and 3
    cr.execute("""
        UPDATE university_semester
        SET academic_year_id = 1,
            semester_type = 'semester_1',
            date_start = '2025-09-01',
            date_end = '2025-12-21',
            active = true
        WHERE id = 2;
    """)

    cr.execute("""
        UPDATE university_semester
        SET academic_year_id = 1,
            semester_type = 'semester_2',
            date_start = '2026-01-05',
            date_end = '2026-04-26',
            active = true
        WHERE id = 3;
    """)

    # 4. Merge duplicate / junk semesters
    # S1, Year1 -> merge into 2, delete unreferenced
    for old_id in [13, 1164]:
        cr.execute("SELECT id FROM university_semester WHERE id = %s;", (old_id,))
        if cr.fetchone():
            _repoint_semester(cr, old_id, 2)
            cr.execute("DELETE FROM university_semester WHERE id = %s;", (old_id,))

    # Semester2 duplicate -> merge into 3, delete unreferenced
    cr.execute("SELECT id FROM university_semester WHERE id = 2988;")
    if cr.fetchone():
        _repoint_semester(cr, 2988, 3)
        cr.execute("DELETE FROM university_semester WHERE id = 2988;")

    # Full Semester (Summer) -> repoint any references to 2, archive 1 (do not delete)
    cr.execute("SELECT id FROM university_semester WHERE id = 1;")
    if cr.fetchone():
        _repoint_semester(cr, 1, 2)
        cr.execute("""
            UPDATE university_semester 
            SET academic_year_id = 1,
                semester_type = 'summer',
                active = false 
            WHERE id = 1;
        """)

    # 5. Clean up department terms
    # Repoint any references to bad terms and clean invalid ones
    cr.execute("""
        SELECT id FROM university_department_term 
        WHERE date_start < '2025-09-01' OR date_end > '2026-06-30'
           OR teaching_weeks < 14;
    """)
    bad_terms = [r[0] for r in cr.fetchall()]
    for tid in bad_terms:
        cr.execute("SELECT 1 FROM university_class_section WHERE term_id = %s;", (tid,))
        if not cr.fetchone():
            cr.execute("DELETE FROM university_department_term WHERE id = %s;", (tid,))
        else:
            cr.execute("UPDATE university_department_term SET active = false WHERE id = %s;", (tid,))

    # Regenerate 16-week terms for all active departments
    semesters = [
        (2, datetime.date(2025, 9, 1), datetime.date(2025, 12, 21)),
        (3, datetime.date(2026, 1, 5), datetime.date(2026, 4, 26)),
    ]
    cr.execute("SELECT id, name FROM university_department WHERE active = true;")
    depts = cr.fetchall()
    for dept_id, dept_name in depts:
        for sem_id, start_d, end_d in semesters:
            cr.execute("""
                SELECT id FROM university_department_term 
                WHERE department_id = %s AND semester_id = %s;
            """, (dept_id, sem_id))
            row = cr.fetchone()
            if row:
                cr.execute("""
                    UPDATE university_department_term
                    SET date_start = %s,
                        date_end = %s,
                        teaching_weeks = 16.0,
                        state = 'approved',
                        active = true
                    WHERE id = %s;
                """, (start_d, end_d, row[0]))
            else:
                name = f"{dept_name} - Semester {1 if sem_id == 2 else 2}"
                cr.execute("""
                    INSERT INTO university_department_term 
                    (name, department_id, semester_id, date_start, date_end, teaching_weeks, state, active, create_date, write_date)
                    VALUES (%s, %s, %s, %s, %s, 16.0, 'approved', true, NOW(), NOW());
                """, (name, dept_id, sem_id, start_d, end_d))

    # 6. Set system parameters
    ICP = env["ir.config_parameter"].sudo()
    ICP.set_param("school_management.current_academic_year_id", "1")
    ICP.set_param("school_management.current_semester_id", "2")
    ICP.set_param("school_management.min_teaching_weeks", "14.0")

    # Invalidate cache so everything is fresh
    env.invalidate_all()


def _repoint_semester(cr, old_id, new_id):
    sem_repoints = [
        ("university_student", "current_semester_id"),
        ("university_enrollment", "semester_id"),
        ("university_fee", "semester_id"),
        ("university_assessment_result", "semester_id"),
        ("university_assignment_submission", "semester_id"),
        ("university_timetable_slot", "semester_id"),
        ("university_exam", "semester_id"),
        ("university_class_section", "semester_id"),
    ]
    for tbl, col in sem_repoints:
        cr.execute(f"""
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = %s AND column_name = %s;
        """, (tbl, col))
        if cr.fetchone():
            cr.execute(f"UPDATE {tbl} SET {col} = %s WHERE {col} = %s;", (new_id, old_id))
