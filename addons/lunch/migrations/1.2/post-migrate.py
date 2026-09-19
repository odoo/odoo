from odoo.db import schema


def migrate(cr, version):
    if not version:
        return
    schema.drop_columns(cr, "lunch_order", ["category_id", "supplier_id", "currency_id"])
    schema.drop_columns(cr, "lunch_product", ["company_id"])
    schema.drop_columns(cr, "lunch_supplier", ["company_id"])
