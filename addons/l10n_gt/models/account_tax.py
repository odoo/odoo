# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class AccountTax(models.Model):
    _inherit = 'account.tax'

    l10n_gt_minimum_base_threshold = fields.Float(
        string="Minimum Base Threshold",
        digits='Account',
        help="The withholding only applies once the untaxed amount of the document reaches this amount.",
    )
    l10n_gt_max_taxable_base = fields.Float(
        string="Maximum Taxable Base",
        digits='Account',
        help="Part of the base above this amount is not withheld by this tax. Leave empty for no limit.",
    )
    l10n_gt_nontaxable_base = fields.Float(
        string="Non-Taxable Base",
        digits='Account',
        help="This amount is deducted from the base before applying the tax.",
    )
