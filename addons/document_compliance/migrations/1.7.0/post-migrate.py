import logging

from odoo.db.schema import column_exists

_logger = logging.getLogger(__name__)

DROPPED_COLUMNS = ["auto_renew_days_before", "template_attachment_id"]

DROPPED_TAG_XMLIDS = [
    "documents_tag_current",
    "documents_tag_expired",
    "documents_tag_near_expire",
]

TAG_RELATIONS = [
    ("document_tag_rel", "document_tag_id"),
    ("document_type_tag_rel", "tag_id"),
    ("document_alias_tag_rel", "document_tag_id"),
    ("document_tag_mail_activity_type_rel", "document_tag_id"),
    ("document_request_wizard_document_tag_rel", "document_tag_id"),
]


def migrate(cr, version):
    if not version:
        return

    for column in DROPPED_COLUMNS:
        if column_exists(cr, "document_type", column):
            cr.execute(f"ALTER TABLE document_type DROP COLUMN {column}")
            _logger.info("Dropped unused column document_type.%s", column)

    cr.execute(
        """
        SELECT name, res_id FROM ir_model_data
        WHERE module = 'document_compliance' AND model = 'document.tag'
          AND name = ANY(%s)
        """,
        [DROPPED_TAG_XMLIDS],
    )
    for name, tag_id in cr.fetchall():
        if _tag_is_referenced(cr, tag_id):
            cr.execute(
                """
                DELETE FROM ir_model_data
                WHERE module = 'document_compliance' AND name = %s
                """,
                [name],
            )
            _logger.warning(
                "Tag %r (id %s) is still applied somewhere, so it is kept and "
                "disowned from this module rather than deleted.",
                name,
                tag_id,
            )
        else:
            cr.execute(
                """
                DELETE FROM ir_model_data
                WHERE module = 'document_compliance' AND name = %s
                """,
                [name],
            )
            cr.execute("DELETE FROM document_tag WHERE id = %s", [tag_id])
            _logger.info("Deleted unused tag %r (id %s).", name, tag_id)


def _tag_is_referenced(cr, tag_id):
    for table, column in TAG_RELATIONS:
        cr.execute(
            "SELECT 1 FROM information_schema.tables WHERE table_name = %s", [table]
        )
        if not cr.fetchone():
            continue
        cr.execute(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = %s AND column_name = %s",
            [table, column],
        )
        if not cr.fetchone():
            continue
        cr.execute(f"SELECT 1 FROM {table} WHERE {column} = %s LIMIT 1", [tag_id])
        if cr.fetchone():
            return True
    return False
