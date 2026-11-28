"""Backfill the new academic-year workflow state after schema creation."""


def migrate(cr, version):
    cr.execute(
        """
        UPDATE university_academic_year
           SET state = 'draft'
         WHERE state IS NULL
        """
    )
