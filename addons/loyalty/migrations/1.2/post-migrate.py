from odoo.db import schema


def migrate(cr, version):
    if not version:
        return
    schema.drop_columns(cr, "loyalty_card", ["company_id"])
    schema.drop_columns(cr, "loyalty_history", ["company_id"])
    schema.drop_columns(cr, "loyalty_reward", ["company_id"])
    schema.drop_columns(cr, "loyalty_rule", ["company_id"])
