from odoo.db import schema


def migrate(cr, version):
    if not version:
        return
    schema.drop_columns(
        cr, "res_partner_relation", ["category", "degree", "weight_risk"]
    )
