# -*- coding: utf-8 -*-
from openerp import models, fields, api, _
from openerp.exceptions import UserError, RedirectWarning, ValidationError
from yahoo import YahooFinance as YAHOO
from oanda import OandaExchange as OANDA
import logging
_logger = logging.getLogger(__name__)

class res_company(models.Model):
    """inherits base company model and exchange rate fields and methods """
    _inherit = "res.company"

    update_rate = fields.Boolean('Automatically Update Rates', help="Turn on/off automatic update of your list of active currencies", default=True)
    rate_source = fields.Selection([('yahoo', 'Yahoo Finance'), ('oanda', 'Oanda.com')], string="Exchange Rate Source")
    quotes = fields.Many2many('res.currency', string="Currency Rates to Update")
    #OANDA specific fields
    api_key = fields.Char('API Key', help="This is your key given by Oanda.com when you subscribe")

    @api.model
    def cron_update_rate(self):
	companies = self.env['res.company'].search([])
	for company in companies:
	    if company.update_rate:
	       company.button_update_rate()
	return True

    @api.one
    def button_update_rate(self):
        """Update the currency rates by pressing a button"""
	quotes = []
	if self.currency_id.rate != 1.0:
	   self.env['res.currency.rate'].search([('currency_id', '=', self.currency_id.id), ('company_id', '=', self.id)]).unlink()
	if self.quotes:
	   for quote in self.quotes:
	       quotes.append(quote.name)
	else:
	    raise ValidationError (_('You must select currencies to update their exchange rates'))

        if self.rate_source == 'yahoo':
	   rates = YAHOO()._update_xrate(self.currency_id.name, quotes)
	   res = self.save_new_rates(rates)
	   _logger.info('Yahoo Finance Exchange rates: %s' % rates)
	elif self.rate_source == 'oanda':
	   rates = OANDA()._update_xrate(self.currency_id.name, quotes, self.api_key)
	   res = self.save_new_rates(rates)
	   _logger.info('Oanda.com Exchange rates: %s' % rates)
	else:
	   raise ValidationError (_('Select the source for your exchange rates'))
	return res

    @api.one
    def save_new_rates(self, rates):
        if rates:
           rate_obj = self.env['res.currency.rate']
           for name, rate in rates.items():
               currency = self.quotes.search([('name', '=', name)], limit=1)
               if currency:
                  rate_obj.search([('currency_id', '=', currency.id), ('company_id', '=', self.id)]).unlink()
                  rate_obj.create({'rate': rate, 'company_id': self.id, 'currency_id': currency.id})
               else:
                 raise ValidationError(_('Error in updating exchange rate for currency: %s') % name)
	else:
	   raise ValidationError(_('No exchange rates to update'))
        return True

