from odoo.db.schema import column_exists

COLUMNS = (
    "stock_sms_confirmation_template_id",
    "has_received_warning_stock_sms",
)


def migrate(cr, version):
    if not version:
        return
    for column in COLUMNS:
        if column_exists(cr, "res_company", column):
            cr.execute(f"ALTER TABLE res_company DROP COLUMN {column} CASCADE")
