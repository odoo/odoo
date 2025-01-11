# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class AccountTax(models.Model):

    _inherit = 'account.tax'

    l10n_ar_type_tax_use = fields.Selection(
        selection=[
            ('sale', 'Sales'),
            ('purchase', 'Purchases'),
            ('none', 'Other'),
            ('supplier', 'Vendor Payment Withholding'),
            ('customer', 'Customer Payment Withholding')
        ],
        compute='_compute_l10n_ar_type_tax_use', inverse='_inverse_l10n_ar_type_tax_use',
        string="Argentina Tax Type"
    )
    l10n_ar_withholding_payment_type = fields.Selection(
        selection=[('supplier', 'Vendor Payment'), ('customer', 'Customer Payment')],
        string="Argentina Withholding Payment Type",
        help="Withholding tax for supplier or customer payments.")
    l10n_ar_tax_type = fields.Selection(
        string='WTH Tax',
        selection=[
            ('earnings', 'Earnings'),
            ('earnings_scale', 'Earnings Scale'),
            ('iibb_untaxed', 'IIBB Untaxed'),
            ('iibb_total', 'IIBB Total Amount'),
        ]
    )
    l10n_ar_withholding_sequence_id = fields.Many2one(
        'ir.sequence',
        string='WTH Sequence',
        check_company=True,
        help='If no sequence provided then it will be required for you to enter withholding number when registering one.')
    l10n_ar_code = fields.Char('AFIP Code')
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

    @api.depends('type_tax_use', 'l10n_ar_withholding_payment_type')
    def _compute_l10n_ar_type_tax_use(self):
        for tax in self:
            if tax.type_tax_use in ('sale', 'purchase'):
                tax.l10n_ar_type_tax_use = tax.type_tax_use
            elif tax.l10n_ar_withholding_payment_type in ('supplier', 'customer'):
                tax.l10n_ar_type_tax_use = tax.l10n_ar_withholding_payment_type
            else:
                tax.l10n_ar_type_tax_use = 'none'

    @api.onchange('l10n_ar_type_tax_use')
    def _inverse_l10n_ar_type_tax_use(self):
        for tax in self:
            if tax.l10n_ar_type_tax_use in ('sale', 'purchase'):
                tax.type_tax_use = tax.l10n_ar_type_tax_use
                tax.l10n_ar_tax_type = False
                tax.l10n_ar_state_id = False
                tax.l10n_ar_withholding_payment_type = False
            else:
                if tax.l10n_ar_type_tax_use in ('supplier', 'customer'):
                    tax.l10n_ar_withholding_payment_type = tax.l10n_ar_type_tax_use
                else:
                    tax.l10n_ar_withholding_payment_type = False
                    tax.l10n_ar_tax_type = False
                tax.type_tax_use = 'none'
