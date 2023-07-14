# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
import logging

from odoo import models
from odoo.tools import float_repr


_logger = logging.getLogger(__name__)


def format_alphanumeric(text, maxlen=None):
    if not text:
        return False
    text = text.encode('latin-1', 'replace').decode('latin-1')
    if maxlen and maxlen > 0:
        text = text[:maxlen]
    elif maxlen and maxlen < 0:
        text = text[maxlen:]
    return text

def format_date(dt):
    # Format the date in the italian standard.
    dt = dt or datetime.now()
    return dt.strftime('%Y-%m-%d')

def format_monetary(number, currency):
    # Format the monetary values to avoid trailing decimals (e.g. 90.85000000000001).
    return float_repr(number, min(2, currency.decimal_places))

def format_numbers(number):
    #format number to str with between 2 and 8 decimals (event if it's .00)
    number_splited = str(number).split('.')
    if len(number_splited) == 1:
        return "%.02f" % number

    cents = number_splited[1]
    if len(cents) > 8:
        return "%.08f" % number
    return float_repr(number, max(2, len(cents)))

def format_numbers_two(number):
    #format number to str with 2 (event if it's .00)
    return "%.02f" % number

def format_phone(number):
    if not number:
        return False
    number = number.replace(' ', '').replace('/', '').replace('.', '')
    if len(number) > 4 and len(number) < 13:
        return format_alphanumeric(number)
    return False

def format_address(street, street2, maxlen=60):
    street, street2 = street or '', street2 or ''
    if street and len(street) >= maxlen:
        street2 = ''
    sep = ' ' if street and street2 else ''
    return format_alphanumeric(f"{street}{sep}{street2}", maxlen)


class L10nItEdiExport(models.AbstractModel):
    _name = 'l10n_it_edi.export'
    _description = "Export invoices and bills into IT EDI XML"

    def _l10n_it_edi_get_formatters(self):
        return {
            'format_date': format_date,
            'format_monetary': format_monetary,
            'format_numbers': format_numbers,
            'format_numbers_two': format_numbers_two,
            'format_phone': format_phone,
            'format_alphanumeric': format_alphanumeric,
            'format_address': format_address,
        }

    def _l10n_it_edi_export(self, move):
        ''' Create the xml file content.
            :return:    The XML content as str.
        '''
        qweb_template_name = (
            'l10n_it_edi.account_invoice_it_FatturaPA_export' if not move._l10n_it_edi_is_simplified()
            else 'l10n_it_edi.account_invoice_it_simplified_FatturaPA_export')
        return self.env['ir.qweb']._render(qweb_template_name, {
            **move._l10n_it_edi_get_values(),
            **self._l10n_it_edi_get_formatters(),
        })
