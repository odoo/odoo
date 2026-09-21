from odoo.db.schema import column_exists

COLUMNS = ("l10n_ke_cu_proxy_address",)


def migrate(cr, version):
    if not version:
        return
    for column in COLUMNS:
        if column_exists(cr, "res_company", column):
            cr.execute(f"ALTER TABLE res_company DROP COLUMN {column} CASCADE")
