# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_ar_tax_base_account_id = fields.Many2one(
        comodel_name='account.account',
        string="Tax Base Account",
        help="Account that will be set on lines created to represent the tax base amounts.")
