from odoo.db.schema import column_exists

COLUMNS = (
    "account_peppol_contact_email",
    "account_peppol_phone_number",
    "account_peppol_proxy_state",
    "peppol_purchase_journal_id",
    "peppol_external_provider",
    "peppol_metadata",
    "peppol_metadata_updated_at",
    "peppol_activate_self_billing_sending",
    "peppol_self_billing_reception_journal_id",
)


def migrate(cr, version):
    if not version:
        return
    for column in COLUMNS:
        if column_exists(cr, "res_company", column):
            cr.execute(f"ALTER TABLE res_company DROP COLUMN {column} CASCADE")
