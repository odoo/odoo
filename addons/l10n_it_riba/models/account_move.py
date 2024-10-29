import logging
from itertools import starmap

from odoo import fields, models

_logger = logging.getLogger(__name__)


def transform(item):
    if isinstance(item, tuple):
        match item:
            case key, str() as fmt, *_:
                pass
            case key, 'date':
                fmt = '%d%m%y'
        return f'{{{key}:{fmt}}}'
    else:
        return item


def trim_value(value, item):
    trim = False
    if isinstance(item, tuple):
        match item:
            case _, _, int() as trim:
                pass
    if trim:
        value = value[:trim]
    return value


def format_record(line, line_template):
    result = (transform(item).format(**line) for item in line_template)
    print(list(result))
    return "".join(starmap(trim_value, zip(result, line_template)))


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _mock_ib(self):
        return self._l10n_it_riba_record_ib({
            'sender_code': '1222222222222',
            'receiver_code': '2',
            'today': fields.Date.today(),
            'support_name': 'abracadabra',
            'sender_note': 'dunno',
            'flow_kind': '1',
            'flow_specifier': '$',
            'currency': 'E',
            'gateway_bank_abi': '01234',
        })

    def _mock_ef(self):
        return self._l10n_it_riba_record_ef({
            'sender_code': '1222222222222',
            'receiver_code': '2',
            'today': fields.Date.today(),
            'support_name': 'abracadabra',
            'sender_note': 'dunno',
            'n_riba': '10',
            'negative_total': 304,
            'positive_total': 602,
            'n_records': 12,
            'currency': 'E',
        })

    def _l10n_it_riba_record_ib(self, line):
        """ Header record """
        format_record(line, (
            ' ',                               # filler
            'IB',                              # record type
            ('sender_code', '<04', 4),
            ('receiver_code', '<04', 4),
            ('today', 'date'),
            ('support_name', '<20', 20),       # must be unique per date, sender, receiver
            ('sender_note', '<6', 6),
            f'{" ":<58}',                      # filler
            ('flow_kind', '1', 1),             # 1 if ecommerce
            ('flow_specifier', '1', 1),        # fixed to '$' only if flow_kind is present
            ('gateway_bank_abi', '>05', 5),    # only if flow_kind is present
            '  ',                              # filler
            ('currency', '1', 1),              # Currency, Euros fixed
            ' ',                               # filler
            '     ',                           # reserved
        ))

    def _l10n_it_riba_record_ef(self, line):
        """ Footer record """
        format_record(line, (
            ' ',                               # filler
            'EF',                              # record type
            ('sender_code', '<04', 4),
            ('receiver_code', '<04', 4),
            ('today', 'date'),
            ('support_name', '<20', 20),       # must be unique per date, sender, receiver
            ('sender_note', '<6', 6),
            ('n_riba', '>07', 7),
            ('negative_total', '>014', 14),
            ('positive_total', '>014', 14),
            ('n_records', '>07', 7),
            f'{" ":<24}',                      # filler
            ('currency', '1', 1),              # Currency, Euros fixed
            '     ',                           # reserved
        ))
