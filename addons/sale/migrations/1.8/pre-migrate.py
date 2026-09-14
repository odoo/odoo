from odoo.db.schema import column_exists, create_column


def migrate(cr, version):
    if not version:
        return
    if not column_exists(cr, "sale_order", "sale_order_template_id"):
        create_column(cr, "sale_order", "sale_order_template_id", "int4")
