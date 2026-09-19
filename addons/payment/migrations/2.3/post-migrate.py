from odoo.db import schema


def migrate(cr, version):
    if not version:
        return
    schema.drop_columns(cr, "payment_token", ["company_id"])
    schema.drop_columns(cr, "payment_transaction", ["company_id"])
