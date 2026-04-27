# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class AccountTax(models.Model):
    _inherit = 'account.tax'

    l10n_ke_tax_type_id = fields.Many2one(
        comodel_name='l10n_ke_edi_oscu.code',
        string="KRA Tax Code",
        domain=[('code_type', '=', '04')],
        compute='_compute_l10n_ke_tax_type_id',
        store=True,
        readonly=False,
        help="KRA code that describes a tax rate or exemption.",
    )

    @api.depends('amount')
    def _compute_l10n_ke_tax_type_id(self):
        code_map = {
            code['tax_rate']: code['id']
            for code in self.env['l10n_ke_edi_oscu.code'].search_read(
                [
                    ('code_type', '=', '04'),
                    ('tax_rate', '!=', 0.0),
                ],
                ['tax_rate'],
            )
        }
        for tax in self:
            if not tax.l10n_ke_tax_type_id or tax.amount in code_map:
                tax.l10n_ke_tax_type_id = code_map.get(tax.amount, False)
