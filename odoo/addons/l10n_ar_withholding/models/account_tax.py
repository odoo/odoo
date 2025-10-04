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

    @api.depends('type_tax_use', 'country_code')
    def _compute_l10n_ar_withholding_payment_type(self):
        self.filtered(lambda x: not x.l10n_ar_withholding_payment_type or x.type_tax_use != 'none' or x.country_code != 'AR').l10n_ar_withholding_payment_type = False
