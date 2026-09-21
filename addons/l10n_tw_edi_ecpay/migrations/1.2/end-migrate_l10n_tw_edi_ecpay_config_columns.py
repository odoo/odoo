from odoo.db.schema import column_exists

COLUMNS = (
    "l10n_tw_edi_ecpay_staging_mode",
    "l10n_tw_edi_ecpay_merchant_id",
    "l10n_tw_edi_ecpay_hashkey",
    "l10n_tw_edi_ecpay_hashIV",
)


def migrate(cr, version):
    if not version:
        return
    for column in COLUMNS:
        if column_exists(cr, "res_company", column):
            cr.execute(f"ALTER TABLE res_company DROP COLUMN {column} CASCADE")
