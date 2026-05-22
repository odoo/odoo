# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class AccountTax(models.Model):
    _inherit = 'account.tax'

    l10n_ar_tax_type = fields.Selection(
        string='WTH Tax',
        selection=[
            ('earnings', 'Earnings'),
            ('earnings_scale', 'Earnings Scale'),
            ('iibb_untaxed', 'IIBB Untaxed'),
            ('iibb_total', 'IIBB Total Amount'),
        ]
    )
    l10n_ar_code = fields.Char('ARCA Code')
    l10n_ar_non_taxable_amount = fields.Float(
        string='Non Taxable Amount',
        digits='Account',
        help="Until this base amount, the tax is not applied."
    )
    l10n_ar_minimum_threshold = fields.Float(
        string="Minimum Treshold",
        help="If the calculated withholding tax amount is lower than minimum withholding threshold then it is 0.0.")
    l10n_ar_state_id = fields.Many2one(
        'res.country.state', string="Jurisdiction", ondelete='restrict', domain="[('country_id', '=?', country_id)]")
    l10n_ar_scale_id = fields.Many2one(
        comodel_name='l10n_ar.earnings.scale',
        string="Scale", help="Earnings table scale if tax type is 'Earnings Scale'."
    )
