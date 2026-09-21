from odoo.db.schema import column_exists

COLUMNS = (
    "account_check_printing_layout",
    "account_check_printing_date_label",
    "account_check_printing_multi_stub",
    "account_check_printing_margin_top",
    "account_check_printing_margin_left",
    "account_check_printing_margin_right",
)


def migrate(cr, version):
    if not version:
        return
    for column in COLUMNS:
        if column_exists(cr, "res_company", column):
            cr.execute(f"ALTER TABLE res_company DROP COLUMN {column} CASCADE")
