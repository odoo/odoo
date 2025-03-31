# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, Command, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    # Migrate wrong data tag on account cuenta102_02
    debit_tag = env.ref('l10n_mx.tag_debit_balance_account')
    credit_tag = env.ref('l10n_mx.tag_credit_balance_account')
    account_102_ids = env['ir.model.data'].search([
        ('name', 'ilike', '%_cuenta102_02'),
        ('model', '=', 'account.account'),
    ]).mapped('res_id')
    accounts_102 = env['account.account'].browse(account_102_ids)
    accounts_102.tag_ids = [Command.unlink(credit_tag.id), Command.link(debit_tag.id)]
