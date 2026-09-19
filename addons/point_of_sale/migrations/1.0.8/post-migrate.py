from odoo.db import schema


def migrate(cr, version):
    if not version:
        return
    schema.drop_columns(cr, "pos_order", ["sale_journal"])
    schema.drop_columns(cr, "pos_order_line", ["company_id"])
    schema.drop_columns(cr, "pos_payment", ["session_id", "company_id"])
