from odoo.db.schema import column_exists

COLUMNS = (
    "internal_transit_location_id",
    "stock_move_email_validation",
    "stock_mail_confirmation_template_id",
    "annual_inventory_month",
    "annual_inventory_day",
    "horizon_days",
    "stock_text_confirmation",
    "stock_confirmation_type",
)


def migrate(cr, version):
    if not version:
        return
    for column in COLUMNS:
        if column_exists(cr, "res_company", column):
            cr.execute(f"ALTER TABLE res_company DROP COLUMN {column} CASCADE")
