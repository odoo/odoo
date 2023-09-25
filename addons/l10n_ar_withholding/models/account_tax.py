# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, api


class AccountTax(models.Model):

    _inherit = 'account.tax'

    l10n_ar_withholding = fields.Selection(
        [('supplier', 'Supplier'), ('customer', 'Customer')], 'Argentinean Withholding')
    l10n_ar_withholding_amount_type = fields.Selection([
        ('untaxed_amount', 'Untaxed Amount'),
        ('total_amount', 'Total Amount'),
    ], 'Withholding Base Amount', help='Base amount used to get withholding amount',)
    l10n_ar_withholding_sequence_id = fields.Many2one(
        'ir.sequence', 'Withholding Number Sequence', copy=False,
        domain=[('code', '=', 'l10n_ar.account.tax.withholding')],
        help='If no sequence provided then it will be required for you to enter withholding number when registering one.',)

    def _get_tax_vals(self, company, tax_template_to_tax):
        vals = super()._get_tax_vals(company, tax_template_to_tax)
        vals.update({
            'l10n_ar_withholding': self.l10n_ar_withholding,
            'l10n_ar_withholding_amount_type': self.l10n_ar_withholding_amount_type,
            'l10n_ar_withholding_sequence_id': self.l10n_ar_withholding_sequence_id,
        })
        return vals

    def ensure_withholding_sequence(self):
        for rec in self.filtered(lambda x: x.l10n_ar_withholding == 'supplier' and not x.l10n_ar_withholding_sequence_id):
            rec.l10n_ar_withholding_sequence_id = self.env['ir.sequence'].create({
                'implementation': 'standard',
                'name': rec.name,
                'padding': 8,
                'number_increment' :1,
            })
