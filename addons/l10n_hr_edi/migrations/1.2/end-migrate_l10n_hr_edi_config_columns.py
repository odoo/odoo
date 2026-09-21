from odoo.db.schema import column_exists

COLUMNS = (
    "l10n_hr_mer_username",
    "l10n_hr_mer_company_ident",
    "l10n_hr_mer_software_ident",
    "l10n_hr_mer_connection_state",
    "l10n_hr_mer_connection_mode",
    "l10n_hr_mer_purchase_journal_id",
)


def migrate(cr, version):
    if not version:
        return
    for column in COLUMNS:
        if column_exists(cr, "res_company", column):
            cr.execute(f"ALTER TABLE res_company DROP COLUMN {column} CASCADE")
