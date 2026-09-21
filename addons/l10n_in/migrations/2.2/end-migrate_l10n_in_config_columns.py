from odoo.db.schema import column_exists

COLUMNS = (
    "l10n_in_upi_id",
    "l10n_in_hsn_code_digit",
    "l10n_in_edi_production_env",
    "l10n_in_tds_feature",
    "l10n_in_tcs_feature",
    "l10n_in_withholding_account_id",
    "l10n_in_withholding_journal_id",
    "l10n_in_is_gst_registered",
    "l10n_in_gstin_status_feature",
)


def migrate(cr, version):
    if not version:
        return
    for column in COLUMNS:
        if column_exists(cr, "res_company", column):
            cr.execute(f"ALTER TABLE res_company DROP COLUMN {column} CASCADE")
