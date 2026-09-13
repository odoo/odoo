from odoo import models
from dateutil.relativedelta import relativedelta
from odoo import fields


class ResCurrency(models.Model):
    _inherit = 'res.currency'

    def _get_rates_query(self, company, date, currency_ids=None):
        """ Get the query to fetch all current rate/date by currency for a specific company/date. """
        # Check if the live exchange rate provider is explicitly set to SUNAT
        if company.currency_provider == 'bcrp':
            return super()._get_rates_query(company, fields.Date.from_string(date) + relativedelta(days=1), currency_ids)
        return super()._get_rates_query(company, date, currency_ids)
