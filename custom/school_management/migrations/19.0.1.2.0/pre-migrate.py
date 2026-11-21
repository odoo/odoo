"""Pre-migration for v19.0.1.2.0: backfill program_id before it becomes NOT NULL.

Existing (pre-redesign) enrollment rows were subject/section based and did not
carry a program_id. This runs before the ORM adds the required column on this
version.

Source order:
  1. linked class section's program_id,
  2. the student's program_id,
  3. the subject's first linked program.
"""


def migrate(cr, version):
    cr.execute(
        "SELECT to_regclass('public.university_enrollment') IS NOT NULL"
    )
    if not cr.fetchone()[0]:
        # Fresh install: no pre-existing table, nothing to backfill.
        return

    cr.execute(
        "ALTER TABLE university_enrollment "
        "ADD COLUMN IF NOT EXISTS program_id integer"
    )
    cr.execute(
        """
        UPDATE university_enrollment en
           SET program_id = sec.program_id
          FROM university_class_section sec
         WHERE sec.id = en.section_id
           AND en.program_id IS NULL
           AND sec.program_id IS NOT NULL
        """
    )
    cr.execute(
        """
        UPDATE university_enrollment en
           SET program_id = stu.program_id
          FROM university_student stu
         WHERE stu.id = en.student_id
           AND en.program_id IS NULL
           AND stu.program_id IS NOT NULL
        """
    )
    cr.execute(
        """
        UPDATE university_enrollment en
           SET program_id = pr.program_id
          FROM (
               SELECT DISTINCT ON (subject_id) subject_id, program_id
                 FROM university_program_subject_rel
                ORDER BY subject_id, program_id
               ) pr
         WHERE pr.subject_id = en.subject_id
           AND en.program_id IS NULL
        """
    )