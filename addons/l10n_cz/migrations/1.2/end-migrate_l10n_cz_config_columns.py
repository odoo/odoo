from odoo.db.schema import column_exists

COLUMNS = (
    "trade_registry",
    "l10n_cz_tax_office_id",
)


def migrate(cr, version):
    if not version:
        return
    for column in COLUMNS:
        if column_exists(cr, "res_company", column):
            cr.execute(f"ALTER TABLE res_company DROP COLUMN {column} CASCADE")
