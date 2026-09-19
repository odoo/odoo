from odoo.db import schema


def migrate(cr, version):
    if not version:
        return
    schema.drop_columns(cr, "account_partial_reconcile", ["debit_currency_id", "credit_currency_id"])
    schema.drop_columns(cr, "account_payment", ["payment_method_id"])
