from odoo import SUPERUSER_ID, api


def mx_update_account_type(cr):
    with api.Environment.manage():
        env = api.Environment(cr, SUPERUSER_ID, {})
        account = env.ref('l10n_mx.cuenta108_01', False)
        if account and account.user_type_id == env.ref('account.data_account_type_receivable'):
            account.write({'user_type_id': env.ref('account.data_account_type_current_assets').id})
        account = env.ref('l10n_mx.cuenta108_02', False)
        if account and account.user_type_id == env.ref('account.data_account_type_receivable'):
            account.write({'user_type_id': env.ref('account.data_account_type_current_assets').id})
        account = env.ref('l10n_mx.cuenta801_01', False)
        if account and account.user_type_id == env.ref('account.data_unaffected_earnings'):
            account.write({'user_type_id': env.ref('account.data_account_type_expenses').id})


def migrate(cr, version):
    if not version:
        return
    mx_update_account_type(cr)
