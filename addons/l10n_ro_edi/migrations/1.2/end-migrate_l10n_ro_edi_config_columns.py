from odoo.db.schema import column_exists

COLUMNS = (
    "l10n_ro_edi_client_id",
    "l10n_ro_edi_access_expiry_date",
    "l10n_ro_edi_refresh_expiry_date",
    "l10n_ro_edi_test_env",
    "l10n_ro_edi_anaf_imported_inv_journal_id",
)


def migrate(cr, version):
    if not version:
        return
    for column in COLUMNS:
        if column_exists(cr, "res_company", column):
            cr.execute(f"ALTER TABLE res_company DROP COLUMN {column} CASCADE")
