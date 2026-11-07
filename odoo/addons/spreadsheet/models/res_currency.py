from odoo import api, models


class ResCurrency(models.Model):
    _inherit = "res.currency"

    # TODO remove this method in master. It's not used anymore.
    @api.model
    def get_currencies_for_spreadsheet(self, currency_names):
        """
        Returns the currency structure of provided currency names.
        This function is meant to be called by the spreadsheet js lib,
        hence the formatting of the result.

        :currency_names list(str): list of currency names (e.g.  ["EUR", "USD", "CAD"])
        :return: list of dicts of the form `{ "code": str, "symbol": str, "decimalPlaces": int, "position":str }`
        """
        currencies = self.with_context(active_test=False).search(
            [("name", "in", currency_names)],
        )
        result = []
        for currency_name in currency_names:
            currency = next(filter(lambda curr: curr.name == currency_name, currencies), None)
            if currency:
                currency_data = {
                    "code": currency.name,
                    "symbol": currency.symbol,
                    "decimalPlaces": currency.decimal_places,
                    "position": currency.position,
                }
            else:
                currency_data = None
            result.append(currency_data)
        return result

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
