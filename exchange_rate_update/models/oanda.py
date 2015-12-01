# -*- coding: utf-8 -*-
from datetime import datetime
import json
import logging
from openerp.exceptions import UserError, RedirectWarning, ValidationError
_logger = logging.getLogger(__name__)

class OandaExchange:
    """OANDA Exchange Rate API Methods """

    def _update_xrate(self, base_currency, quotes, api_key):
	new_rates = {}
	quote_string = ''
	today = datetime.today().strftime("%Y-%m-%d")
        if base_currency in quotes:
            quotes.remove(base_currency)
        for quote in quotes:
	    quote_string = quote_string + '&quote=' + quote

	url = ('https://www.oanda.com/rates/api/v1/rates/{}.json?api_key={}&decimal_places=6&date={}'
		'&fields=averages{}'.format(base_currency,api_key,today,quote_string))

        res = json.loads(self.get_rates(url))
	if 'code' in res.keys():
	   raise ValidationError ('OANDA.COM Error Code {}: {}'.format(res['code'], res['message']))
	else:
	   rates = res['quotes']
           #_logger.info('OANDA Exchange Rate API rates: %s' % rates)
	if rates:
	   for name, rate in rates.items():
	       new_rates[name] = rate['bid']
        else:
           raise ValidationError (_('Could not update the %s') % quote)

        return new_rates

    def get_rates(self, url):
        """Returns a string of values from CSV file"""
        try:
            import urllib
            file_obj = urllib.urlopen(url)
            file_read = file_obj.read()
            file_obj.close()
            return file_read
        except ImportError:
            raise ValidationError (_('[urllib] missing try to install python-urllib'))
        except IOError:
            raise ValidationError (_('No connection to Internet'))

