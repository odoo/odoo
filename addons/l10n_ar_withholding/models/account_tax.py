# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class AccountTax(models.Model):

    _inherit = 'account.tax'

    l10n_ar_withholding_payment_type = fields.Selection(
        [('supplier', 'Supplier'), ('customer', 'Customer')], 'Argentinean Withholding Type',
        compute="_compute_l10n_ar_withholding_payment_type", store=True, readonly=False)
    l10n_ar_tax_type = fields.Selection(string='Argentinean Tax Type', selection=[
        ('earnings_withholding', 'Earnings Withholding'),
        ('iibb_withholding', 'IIBB Withholding'),
    ],
        compute="_compute_l10n_ar_tax_type", store=True, readonly=False)
    l10n_ar_withholding_sequence_id = fields.Many2one(
        'ir.sequence', 'Argentinean Withholding Sequence', copy=False, check_company=True,
        help='If no sequence provided then it will be required for you to enter withholding number when registering one.')
    l10n_ar_code = fields.Char('Argentinean Code')
    l10n_ar_withholding_auxiliary_amount = fields.Float(
        'Argentinean Withholding Auxiliary Amount',
        digits='Account',
        help="This field represents differents things regarding the l10n_ar_tax_type"
    )
    l10n_ar_state_id = fields.Many2one(
        'res.country.state', string="Argentinean State", ondelete='restrict', domain="[('country_id', '=?', country_id)]")

    @api.depends('type_tax_use', 'country_code')
    def _compute_l10n_ar_withholding_payment_type(self):
        self.filtered(lambda x: not x.l10n_ar_withholding_payment_type or x.type_tax_use != 'none' or x.country_code != 'AR').l10n_ar_withholding_payment_type = False

    @api.depends('l10n_ar_withholding_payment_type')
    def _compute_l10n_ar_tax_type(self):
        self.filtered(lambda x: not x.l10n_ar_withholding_payment_type).l10n_ar_tax_type = False
