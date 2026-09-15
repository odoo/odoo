import logging

from odoo.db.schema import column_exists

_logger = logging.getLogger(__name__)

OLD_FLAGS = [
    (1, "notification_sent_1"),
    (7, "notification_sent_7"),
    (30, "notification_sent_30"),
]


def migrate(cr, version):
    if not version:
        return

    present = [
        (days, column)
        for days, column in OLD_FLAGS
        if column_exists(cr, "document_document", column)
    ]
    if not present:
        _logger.info("No legacy notification flags to fold; nothing to do.")
        return

    cases = " ".join(f"WHEN {column} THEN {days}" for days, column in present)
    condition = " OR ".join(column for _days, column in present)
    cr.execute(
        f"""
        UPDATE document_document
        SET notification_last_days = CASE {cases} ELSE 0 END
        WHERE {condition}
        """
    )
    _logger.info("Folded legacy notification flags on %d documents", cr.rowcount)

    for _days, column in present:
        cr.execute(f"ALTER TABLE document_document DROP COLUMN {column}")
        _logger.info("Dropped legacy column document_document.%s", column)
