from odoo.db import schema


def migrate(cr, version):
    if not version:
        return
    schema.drop_columns(cr, "sale_order_template_line", ["company_id"])
