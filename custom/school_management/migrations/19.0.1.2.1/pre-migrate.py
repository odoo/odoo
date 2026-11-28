"""19.0.1.2.1 data-integrity migration.

Runs BEFORE the model fields/constraints are reloaded, so it repairs legacy
data that would otherwise violate the new integrity rules:

1. Student academic placement (department/faculty) now derives from the
   selected PROGRAM. Students whose stored department/faculty disagree with
   their program's department/faculty are corrected to match.
2. Legacy faculty.dean_id / department.head_id values no longer reconcile with
   the new source of truth (active academic assignments), so stale values are
   cleared before the derived (stored) fields are recomputed.
3. Student IDs are de-duplicated so the new unique index on student_id holds.
"""

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    _logger.info("school_management 19.0.1.2.1: repairing student academic placement")

    # --- 1. Students: align stored department/faculty with their program ---
    cr.execute(
        """
        UPDATE university_student s
        SET department_id = p.department_id,
            faculty_id = d.faculty_id
        FROM university_program p
        LEFT JOIN university_department d ON d.id = p.department_id
        WHERE s.program_id = p.id
          AND (s.department_id IS DISTINCT FROM p.department_id
               OR s.faculty_id IS DISTINCT FROM d.faculty_id)
        """
    )
    _logger.info("  students aligned to program: %s", cr.rowcount)

    # --- 2. Students without a program should not carry orphan placement ---
    cr.execute(
        """
        UPDATE university_student
        SET department_id = NULL, faculty_id = NULL
        WHERE program_id IS NULL
          AND (department_id IS NOT NULL OR faculty_id IS NOT NULL)
        """
    )
    _logger.info("  students cleared orphan placement: %s", cr.rowcount)

    # --- 3. Facilities/Departments: clear legacy dean/head that are not backed
    #         by an active assignment. The stored derived fields will be
    #         recomputed from assignments by the ORM after this migration. ---
    cr.execute(
        "UPDATE university_faculty f "
        "SET dean_id = NULL "
        "WHERE NOT EXISTS ("
        "  SELECT 1 FROM university_academic_assignment a "
        "  WHERE a.faculty_id = f.id AND a.role IN ('dean','vice_dean') AND a.active"
        ")"
    )
    _logger.info("  stale faculty deans cleared: %s", cr.rowcount)

    cr.execute(
        "UPDATE university_department d "
        "SET head_id = NULL "
        "WHERE NOT EXISTS ("
        "  SELECT 1 FROM university_academic_assignment a "
        "  WHERE a.department_id = d.id AND a.role = 'department_head' AND a.active"
        ")"
    )
    _logger.info("  stale department heads cleared: %s", cr.rowcount)

    # --- 4. De-duplicate NULL / duplicate student_id codes (legacy instances
    #         may share the display student_id). Append a numeric suffix. ---
    cr.execute(
        """
        SELECT student_id, array_agg(id ORDER BY id) AS ids
        FROM university_student
        WHERE student_id IS NOT NULL
        GROUP BY student_id
        HAVING count(*) > 1
        """
    )
    dupes = cr.fetchall()
    for _code, ids in dupes:
        for offset, sid in enumerate(ids, start=1):
            if offset == 1:
                continue
            cr.execute(
                "UPDATE university_student SET student_id = %s WHERE id = %s",
                ("%s-%s" % (_code, offset), sid),
            )

    # The NULL student_id headline (3 students) is a "no code yet" state; the
    # unique index is partial (WHERE student_id IS NOT NULL), so NULLs remain
    # allowed and need no rework.
    _logger.info("school_management 19.0.1.2.1 migration complete")
