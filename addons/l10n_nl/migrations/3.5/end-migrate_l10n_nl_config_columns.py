from odoo.db.schema import column_exists

COLUMNS = (
    "l10n_nl_rounding_difference_loss_account_id",
    "l10n_nl_rounding_difference_profit_account_id",
)


def migrate(cr, version):
    if not version:
        return
    for column in COLUMNS:
        if column_exists(cr, "res_company", column):
            cr.execute(f"ALTER TABLE res_company DROP COLUMN {column} CASCADE")
