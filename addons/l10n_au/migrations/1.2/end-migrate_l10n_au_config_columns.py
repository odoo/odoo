from odoo.db.schema import column_exists

COLUMNS = (
    "l10n_au_is_gst_registered",
    "l10n_au_trading_name",
)


def migrate(cr, version):
    if not version:
        return
    for column in COLUMNS:
        if column_exists(cr, "res_company", column):
            cr.execute(f"ALTER TABLE res_company DROP COLUMN {column} CASCADE")
