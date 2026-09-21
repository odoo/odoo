from odoo.db import schema


def migrate(cr, version):
    if not version:
        return
    # 1.20 as published on origin dropped these; a database upgraded here under
    # the 1.20 the account.config change carried before the 2026-09-20
    # renumbering never ran it. Re-issued so every database converges.
    schema.drop_columns(cr, "account_accrued_orders_wizard", ["currency_id"])
    schema.drop_columns(cr, "account_analytic_line", ["journal_id"])
    schema.drop_columns(cr, "account_fiscal_position_account", ["company_id"])
    schema.drop_columns(cr, "account_move_line", ["tax_group_id"])
    schema.drop_columns(cr, "account_reconcile_model_line", ["company_id"])
    schema.drop_columns(cr, "account_return_check", ["return_state"])
