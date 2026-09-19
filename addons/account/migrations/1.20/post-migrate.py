from odoo.db import schema


def migrate(cr, version):
    if not version:
        return
    schema.drop_columns(cr, "account_accrued_orders_wizard", ["currency_id"])
    schema.drop_columns(cr, "account_analytic_line", ["journal_id"])
    schema.drop_columns(cr, "account_fiscal_position_account", ["company_id"])
    schema.drop_columns(cr, "account_move_line", ["tax_group_id"])
    schema.drop_columns(cr, "account_reconcile_model_line", ["company_id"])
    schema.drop_columns(cr, "account_return_check", ["return_state"])
