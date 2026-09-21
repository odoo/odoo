from odoo.db.schema import column_exists

COLUMNS = (
    "nemhandel_contact_email",
    "nemhandel_phone_number",
    "l10n_dk_nemhandel_proxy_state",
    "nemhandel_purchase_journal_id",
)


def migrate(cr, version):
    if not version:
        return
    for column in COLUMNS:
        if column_exists(cr, "res_company", column):
            cr.execute(f"ALTER TABLE res_company DROP COLUMN {column} CASCADE")
