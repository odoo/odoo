from odoo.db import schema


def migrate(cr, version):
    if not version:
        return
    schema.drop_columns(
        cr,
        "account_move_line",
        ["company_currency_id", "invoice_date", "statement_line_id"],
    )
