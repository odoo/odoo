from odoo import api, fields, models


class ResCurrencyRate(models.Model):
    _inherit = "res.currency.rate"

    @api.model
    def _get_rate_for_spreadsheet(self, currency_from_code, currency_to_code, date=None):
        if not currency_from_code or not currency_to_code:
            return False
        Currency = self.env["res.currency"].with_context({"active_test": False})
        currency_from = Currency.search([("name", "=", currency_from_code)])
        currency_to = Currency.search([("name", "=", currency_to_code)])
        if not currency_from or not currency_to:
            return False
        company = self.env.company
        date = fields.Date.from_string(date) if date else fields.Date.context_today(self)
        return Currency._get_conversion_rate(currency_from, currency_to, company, date)

    @api.model
    def get_rates_for_spreadsheet(self, requests):
        result = []
        for request in requests:
            record = request.copy()
            record.update({
                "rate": self._get_rate_for_spreadsheet(request["from"], request["to"], request.get("date")),
            })
            result.append(record)
        return result
