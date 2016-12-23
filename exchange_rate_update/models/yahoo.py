# -*- coding: utf-8 -*-

class YahooFinance:
    """Yahoo Finance Exchange Rate API Methods """

    def _update_xrate(self, base_currency, quotes):
	new_rates = {}
        url = 'http://download.finance.yahoo.com/d/quotes.csv?s=%s=X&f=sl1c1abg'
        if base_currency in quotes:
            quotes.remove(base_currency)
        for quote in quotes:
            res = self.get_rates(url % (base_currency + quote))
	    print res
            rate = res.split(',')[1]
            if rate:
                new_rates[quote] = rate
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

