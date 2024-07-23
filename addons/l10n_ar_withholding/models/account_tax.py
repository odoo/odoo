# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class AccountTax(models.Model):

    _inherit = 'account.tax'

    l10n_ar_withholding_payment_type = fields.Selection(
        [('supplier', 'Supplier'), ('customer', 'Customer')], 'Argentinean Withholding type',
        compute="_compute_l10n_ar_withholding_payment_type", store=True, readonly=False)

    l10n_ar_withholding_sequence_id = fields.Many2one(
        'ir.sequence', 'Withholding Number Sequence', copy=False, check_company=True,
        help='If no sequence provided then it will be required for you to enter withholding number when registering one.')

    l10n_ar_withholding_accumulated_payments = fields.Selection(string='Accumulated Payments', selection=[
        ('month', 'Month'),
        ('year', 'Year'),
    ], help="If not selected then payments are not accumulated.")

    l10n_ar_withholding_non_taxable_amount = fields.Float(
        'Non-taxable Amount',
        digits='Account',
        help="Amount to be substracted before applying alicuot"
    )

    l10n_ar_tax_type = fields.Selection(string='Tax Type', selection=[
        ('earnings_withholding', 'Earnings Withholding'),
        ('iibb_withholding', 'IIBB Withholding'),
    ])

    l10n_ar_state_id = fields.Many2one(
        'res.country.state', ondelete='restrict', domain="[('country_id', '=?', country_id)]")

    @api.depends('type_tax_use', 'country_code')
    def _compute_l10n_ar_withholding_payment_type(self):
        self.filtered(lambda x: not x.l10n_ar_withholding_payment_type or x.type_tax_use != 'none' or x.country_code != 'AR').l10n_ar_withholding_payment_type = False
