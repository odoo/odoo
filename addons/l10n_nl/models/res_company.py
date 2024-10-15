# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.addons import account, base_vat


class ResCompany(base_vat.ResCompany, account.ResCompany):

    l10n_nl_rounding_difference_loss_account_id = fields.Many2one('account.account', check_company=True)
    l10n_nl_rounding_difference_profit_account_id = fields.Many2one('account.account', check_company=True)
