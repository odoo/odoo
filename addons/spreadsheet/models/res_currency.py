from odoo import api, models


class ResCurrency(models.Model):
    _inherit = "res.currency"

    @api.model
    def get_company_currency_for_spreadsheet(self, company_id=None):
        """
        Returns the currency structure for the currency of the company.
        This function is meant to be called by the spreadsheet js lib,
        hence the formatting of the result.

        :company_id int: Id of the company
        :return: dict of the form `{ "code": str, "symbol": str, "decimalPlaces": int, "position":str }`
        """
        company = self.env["res.company"].browse(company_id) if company_id else self.env.company
        if not company.exists():
            return False
        currency = company.currency_id
        return {
            "code": currency.name,
            "symbol": currency.symbol,
            "decimalPlaces": currency.decimal_places,
            "position": currency.position,
        }
