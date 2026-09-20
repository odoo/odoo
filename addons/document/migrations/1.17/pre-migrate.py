from odoo.db.schema import column_exists


def migrate(cr, version):
    """An activity carries whether a document names it as its request; the
    column is filled here so the ORM does not compute it activity by activity."""
    if not version or column_exists(cr, "mail_activity", "is_document_request"):
        return
    cr.execute("ALTER TABLE mail_activity ADD COLUMN is_document_request boolean")
    cr.execute(
        """
        UPDATE mail_activity a
           SET is_document_request = TRUE
          FROM document_document d
         WHERE d.request_activity_id = a.id
        """
    )
