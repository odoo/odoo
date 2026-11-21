import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Copy first university.subject.book product onto university.subject.book_product_id."""
    cr.execute(
        """
        SELECT 1
        FROM information_schema.tables
        WHERE table_name = 'university_subject_book'
        """
    )
    if not cr.fetchone():
        return

    cr.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'university_subject'
          AND column_name = 'book_product_id'
        """
    )
    if not cr.fetchone():
        cr.execute(
            """
            ALTER TABLE university_subject
            ADD COLUMN IF NOT EXISTS book_product_id INTEGER
            """
        )

    cr.execute(
        """
        UPDATE university_subject AS subject
        SET book_product_id = books.product_id
        FROM (
            SELECT DISTINCT ON (subject_id)
                   subject_id, product_id
            FROM university_subject_book
            WHERE product_id IS NOT NULL
            ORDER BY subject_id, id ASC
        ) AS books
        WHERE subject.id = books.subject_id
          AND subject.book_product_id IS NULL
        """
    )
    _logger.info("Migrated %s subject book product mappings", cr.rowcount)
