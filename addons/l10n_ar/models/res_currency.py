# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, api


class ResCurrency(models.Model):

    _inherit = "res.currency"

    l10n_ar_afip_code = fields.Char('AFIP Code', size=4, help='This code will be used on electronic invoice')

    @api.model
    def _get_conversion_rate(self, from_currency, to_currency, company, date):
        return self._context.get('force_rate', False) or super()._get_conversion_rate(
            from_currency, to_currency, company, date)
