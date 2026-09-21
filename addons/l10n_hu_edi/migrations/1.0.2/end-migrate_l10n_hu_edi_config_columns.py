from odoo.db.schema import column_exists

COLUMNS = (
    "l10n_hu_tax_regime",
    "l10n_hu_edi_server_mode",
    "l10n_hu_edi_username",
    "l10n_hu_edi_last_transaction_recovery",
)


def migrate(cr, version):
    if not version:
        return
    for column in COLUMNS:
        if column_exists(cr, "res_company", column):
            cr.execute(f"ALTER TABLE res_company DROP COLUMN {column} CASCADE")
