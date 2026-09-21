from odoo.db.schema import column_exists

COLUMNS = (
    "point_of_sale_update_stock_quantities",
    "point_of_sale_use_ticket_qr_code",
    "point_of_sale_ticket_unique_code",
    "point_of_sale_ticket_portal_url_display_mode",
)


def migrate(cr, version):
    if not version:
        return
    for column in COLUMNS:
        if column_exists(cr, "res_company", column):
            cr.execute(f"ALTER TABLE res_company DROP COLUMN {column} CASCADE")
