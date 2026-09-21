from odoo.db.schema import column_exists

COLUMNS = (
    "l10n_tr_nilvera_use_test_env",
    "l10n_tr_nilvera_purchase_journal_id",
)


def migrate(cr, version):
    if not version:
        return
    for column in COLUMNS:
        if column_exists(cr, "res_company", column):
            cr.execute(f"ALTER TABLE res_company DROP COLUMN {column} CASCADE")
