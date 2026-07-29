# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class AccountTax(models.Model):
    _inherit = 'account.tax'

    l10n_gt_currency_id = fields.Many2one(
        comodel_name='res.currency',
        compute='_compute_l10n_gt_currency_id',
    )
    l10n_gt_minimum_base_threshold = fields.Monetary(
        string="Minimum Base Threshold",
        currency_field='l10n_gt_currency_id',
        tracking=True,
        help="The withholding only applies once the untaxed amount of the document reaches this amount.",
    )
    l10n_gt_max_taxable_base = fields.Monetary(
        string="Maximum Taxable Base",
        currency_field='l10n_gt_currency_id',
        tracking=True,
        help="Part of the base above this amount is not withheld by this tax. Leave empty for no limit.",
    )
    l10n_gt_nontaxable_base = fields.Monetary(
        string="Non-Taxable Base",
        currency_field='l10n_gt_currency_id',
        tracking=True,
        help="This amount is deducted from the base before applying the tax.",
    )

    def _compute_l10n_gt_currency_id(self):
        self.l10n_gt_currency_id = self.env.ref('base.GTQ')
