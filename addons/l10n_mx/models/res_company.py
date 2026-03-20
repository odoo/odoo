# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_mx_income_return_discount_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Income account for returns and discounts'
    )
    l10n_mx_income_re_invoicing_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Income account for re-invoicing'
    )
