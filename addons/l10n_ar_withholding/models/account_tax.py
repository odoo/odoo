# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class AccountTax(models.Model):

    _inherit = 'account.tax'

    l10n_ar_withholding_payment_type = fields.Selection(
        [('supplier', 'Vendor Payment'), ('customer', 'Customer Payment')], 'AFIP Argentinean Withholding Type',
        compute="_compute_l10n_ar_withholding_payment_type", store=True, readonly=False, help="Withholding tax for supplier or customer payments.")
    l10n_ar_tax_type = fields.Selection(string='Argentinean Tax Type', selection=[
        ('earnings_withholding', 'Earnings'),
        ('earnings_withholding_scale', 'Earnings Scale'),
        ('iibb_withholding_untaxed', 'IIBB Untaxed'),
        ('iibb_withholding_total', 'IIBB Total Amount'),
    ],
        compute="_compute_l10n_ar_tax_type", store=True, readonly=False)
    l10n_ar_withholding_sequence_id = fields.Many2one(
        'ir.sequence', 'AFIP Withholding Sequence', copy=False, check_company=True,
        help='If no sequence provided then it will be required for you to enter withholding number when registering one.')
    l10n_ar_code = fields.Char('Argentinean Code', help="Earning withholding regimen.")
    l10n_ar_non_taxable_amount = fields.Float(
        'Argentinean Non Taxable Amount',
        digits='Account',
        help="Until this base amount, the tax is not applied."
    )
    l10n_ar_state_id = fields.Many2one(
        'res.country.state', string="Argentinean State", ondelete='restrict', domain="[('country_id', '=?', country_id)]")
    l10n_ar_scale_id = fields.Many2one(
        comodel_name='l10n_ar.earnings.scale',
        help="Earnings table scale if tax type is 'Earnings Scale'."
    )
    l10n_ar_withholding_minimum_threshold = fields.Float(default=0.0, help="If the calculated withholding tax amount is lower than minimum withholding threshold then it is 0.0.")

    @api.depends('type_tax_use', 'country_code')
    def _compute_l10n_ar_withholding_payment_type(self):
        self.filtered(lambda x: not x.l10n_ar_withholding_payment_type or x.type_tax_use != 'none' or x.country_code != 'AR').l10n_ar_withholding_payment_type = False

    @api.depends('l10n_ar_withholding_payment_type')
    def _compute_l10n_ar_tax_type(self):
        self.filtered(lambda x: not x.l10n_ar_withholding_payment_type).l10n_ar_tax_type = False
