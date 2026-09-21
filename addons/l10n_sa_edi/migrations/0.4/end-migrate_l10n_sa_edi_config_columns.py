from odoo.db.schema import column_exists

COLUMNS = (
    "l10n_sa_private_key_id",
    "l10n_sa_api_mode",
    "l10n_sa_edi_is_production",
)


def migrate(cr, version):
    if not version:
        return
    for column in COLUMNS:
        if column_exists(cr, "res_company", column):
            cr.execute(f"ALTER TABLE res_company DROP COLUMN {column} CASCADE")
