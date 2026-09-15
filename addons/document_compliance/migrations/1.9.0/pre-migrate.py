from odoo.db.schema import column_exists

EXPIRING_SOON_DAYS = 30


def migrate(cr, version):
    if not version:
        return

    if not column_exists(cr, "document_document", "expiration_state"):
        cr.execute("ALTER TABLE document_document ADD COLUMN expiration_state varchar")
    cr.execute(
        """
        UPDATE document_document
        SET expiration_state = CASE
            WHEN date_expiration < CURRENT_DATE THEN 'expired'
            WHEN date_expiration <= CURRENT_DATE + %s THEN 'expiring_soon'
            ELSE 'valid'
        END
        WHERE date_expiration IS NOT NULL
        """,
        [EXPIRING_SOON_DAYS],
    )
    cr.execute(
        """
        UPDATE document_document d
        SET compliance_state = CASE
            WHEN d.document_type_id IS NULL THEN 'na'
            WHEN dt.has_expiration IS NOT TRUE THEN 'compliant'
            WHEN d.expiration_state IN ('valid', 'expiring_soon') THEN 'compliant'
            ELSE 'non_compliant'
        END
        FROM document_document src
        LEFT JOIN document_type dt ON dt.id = src.document_type_id
        WHERE src.id = d.id
        """
    )
    if column_exists(cr, "document_document", "expired"):
        cr.execute("ALTER TABLE document_document DROP COLUMN expired")
