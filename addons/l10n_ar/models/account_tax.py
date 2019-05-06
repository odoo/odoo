# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, api


class AccountTax(models.Model):

    _inherit = 'account.tax'

    l10n_ar_jurisdiction_code = fields.Char(
        compute='_compute_l10n_ar_jurisdiction_code',
        string="Jurisdiction Code",
    )

    @api.multi
    def _compute_l10n_ar_jurisdiction_code(self):
        for rec in self:
            tag = rec.tag_ids.filtered('l10n_ar_jurisdiction_code')
            rec.l10n_ar_jurisdiction_code = tag and tag[0].l10n_ar_jurisdiction_code
