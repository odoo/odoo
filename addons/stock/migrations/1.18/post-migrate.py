from odoo.db import schema


def migrate(cr, version):
    if not version:
        return
    schema.drop_columns(cr, "stock_move", ["product_tmpl_id"])
    schema.drop_columns(cr, "stock_rule", ["route_sequence"])
