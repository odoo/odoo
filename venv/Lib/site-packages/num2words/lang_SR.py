# -*- coding: utf-8 -*-
# Copyright (c) 2003, Taro Ogawa.  All Rights Reserved.
# Copyright (c) 2013, Savoir-faire Linux inc.  All Rights Reserved.

# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Lesser General Public License for more details.
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA 02110-1301 USA

from __future__ import unicode_literals

from .base import Num2Word_Base
from .currency import parse_currency_parts, prefix_currency
from .utils import get_digits, splitbyx

ZERO = ('nula',)

ONES = {
    1: ('jedan', 'jedna'),
    2: ('dva', 'dve'),
    3: ('tri', 'tri'),
    4: ('četiri', 'četiri'),
    5: ('pet', 'pet'),
    6: ('šest', 'šest'),
    7: ('sedam', 'sedam'),
    8: ('osam', 'osam'),
    9: ('devet', 'devet'),
}

TENS = {
    0: ('deset',),
    1: ('jedanaest',),
    2: ('dvanaest',),
    3: ('trinaest',),
    4: ('četrnaest',),
    5: ('petnaest',),
    6: ('šesnaest',),
    7: ('sedamnaest',),
    8: ('osamnaest',),
    9: ('devetnaest',),
}

TWENTIES = {
    2: ('dvadeset',),
    3: ('trideset',),
    4: ('četrdeset',),
    5: ('pedeset',),
    6: ('šezdeset',),
    7: ('sedamdeset',),
    8: ('osamdeset',),
    9: ('devedeset',),
}

HUNDREDS = {
    1: ('sto',),
    2: ('dvesta',),
    3: ('trista',),
    4: ('četristo',),
    5: ('petsto',),
    6: ('šesto',),
    7: ('sedamsto',),
    8: ('osamsto',),
    9: ('devetsto',),
}

SCALE = {
    0: ('', '', '', False),
    1: ('hiljada', 'hiljade', 'hiljada', True),  # 10^3
    2: ('milion', 'miliona', 'miliona', False),  # 10^6
    3: ('bilion', 'biliona', 'biliona', False),  # 10^9
    4: ('trilion', 'triliona', 'triliona', False),  # 10^12
    5: ('kvadrilion', 'kvadriliona', 'kvadriliona', False),  # 10^15
    6: ('kvintilion', 'kvintiliona', 'kvintiliona', False),  # 10^18
    7: ('sekstilion', 'sekstiliona', 'sekstiliona', False),  # 10^21
    8: ('septilion', 'septiliona', 'septiliona', False),  # 10^24
    9: ('oktilion', 'oktiliona', 'oktiliona', False),  # 10^27
    10: ('nonilion', 'noniliona', 'noniliona', False),  # 10^30
}


class Num2Word_SR(Num2Word_Base):
    CURRENCY_FORMS = {
        'RUB': (
            ('rublja', 'rublje', 'rublji', True),
            ('kopejka', 'kopejke', 'kopejki', True)
        ),
        'EUR': (
            ('evro', 'evra', 'evra', False),
            ('cent', 'centa', 'centi', False)
        ),
        'RSD': (
            ('dinar', 'dinara', 'dinara', False),
            ('para', 'pare', 'para', True)
        ),
    }

    def setup(self):
        self.negword = "minus"
        self.pointword = "zapeta"

    def to_cardinal(self, number, feminine=False):
        n = str(number).replace(',', '.')
        if '.' in n:
            left, right = n.split('.')
            return u'%s %s %s' % (
                self._int2word(int(left), feminine),
                self.pointword,
                self._int2word(int(right), feminine)
            )
        else:
            return self._int2word(int(n), feminine)

    def pluralize(self, number, forms):
        if number % 100 < 10 or number % 100 > 20:
            if number % 10 == 1:
                form = 0
            elif 1 < number % 10 < 5:
                form = 1
            else:
                form = 2
        else:
            form = 2
        return forms[form]

    def to_ordinal(self, number):
        raise NotImplementedError()

    def _cents_verbose(self, number, currency):
        return self._int2word(
            number,
            self.CURRENCY_FORMS[currency][1][-1]
        )

    def _int2word(self, number, feminine=False):
        if number < 0:
            return ' '.join([self.negword, self._int2word(abs(number))])

        if number == 0:
            return ZERO[0]

        words = []
        chunks = list(splitbyx(str(number), 3))
        chunk_len = len(chunks)
        for chunk in chunks:
            chunk_len -= 1
            digit_right, digit_mid, digit_left = get_digits(chunk)

            if digit_left > 0:
                words.append(HUNDREDS[digit_left][0])

            if digit_mid > 1:
                words.append(TWENTIES[digit_mid][0])

            if digit_mid == 1:
                words.append(TENS[digit_right][0])
            elif digit_right > 0:
                is_feminine = feminine or SCALE[chunk_len][-1]
                gender_idx = int(is_feminine)
                words.append(
                    ONES[digit_right][gender_idx]
                )

            if chunk_len > 0 and chunk != 0:
                words.append(self.pluralize(chunk, SCALE[chunk_len]))

        return ' '.join(words)

    def to_currency(self, val, currency='EUR', cents=True, separator=',',
                    adjective=False):
        """
        Args:
            val: Numeric value
            currency (str): Currency code
            cents (bool): Verbose cents
            separator (str): Cent separator
            adjective (bool): Prefix currency name with adjective
        Returns:
            str: Formatted string

        """
        left, right, is_negative = parse_currency_parts(val)

        try:
            cr1, cr2 = self.CURRENCY_FORMS[currency]

        except KeyError:
            raise NotImplementedError(
                'Currency code "%s" not implemented for "%s"' %
                (currency, self.__class__.__name__))

        if adjective and currency in self.CURRENCY_ADJECTIVES:
            cr1 = prefix_currency(
                self.CURRENCY_ADJECTIVES[currency],
                cr1
            )

        minus_str = "%s " % self.negword if is_negative else ""
        cents_str = self._cents_verbose(right, currency) \
            if cents else self._cents_terse(right, currency)

        return u'%s%s %s%s %s %s' % (
            minus_str,
            self.to_cardinal(left, feminine=cr1[-1]),
            self.pluralize(left, cr1),
            separator,
            cents_str,
            self.pluralize(right, cr2)
        )
