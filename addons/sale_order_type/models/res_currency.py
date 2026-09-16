from odoo import api, models


class ResCurrency(models.Model):
    _inherit = "res.currency"

    @api.model
    def _get_conversion_rate(self, from_currency, to_currency, company, date):
        from_currency = from_currency or company.currency_id
        return super()._get_conversion_rate(from_currency, to_currency, company, date)
