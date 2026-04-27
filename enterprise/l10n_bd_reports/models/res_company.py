# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_bd_corporate_tax_liability = fields.Many2one(
        string="Corporate tax liability account",
        comodel_name="account.account",
    )
    l10n_bd_corporate_tax_expense = fields.Many2one(
        string="Corporate tax expense account",
        comodel_name="account.account",
    )
