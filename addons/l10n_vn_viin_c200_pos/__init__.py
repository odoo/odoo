from odoo import api, SUPERUSER_ID


def _correct_default_pos_receivable_account(env):
    for company in env['res.company'].search([('chart_template_id', '=', env.ref('l10n_vn.vn_template').id)]):
        accounts = company.account_default_pos_receivable_account_id
        for pos_payment_method in env['pos.payment.method'].search([('company_id', '=', company.id), ('receivable_account_id', '!=', accounts.id)]):
            pos_payment_method.write({
                'receivable_account_id': accounts
            })

def pre_init_hook(cr):
    env = api.Environment(cr, SUPERUSER_ID, {})
    _correct_default_pos_receivable_account(env)
