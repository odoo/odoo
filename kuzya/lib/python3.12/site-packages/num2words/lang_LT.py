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
from .utils import get_digits, splitbyx

ZERO = ('nulis',)

ONES_FEMININE = {
    1: ('viena',),
    2: ('dvi',),
    3: ('trys',),
    4: ('keturios',),
    5: ('penkios',),
    6: ('šešios',),
    7: ('septynios',),
    8: ('aštuonios',),
    9: ('devynios',),
}

ONES = {
    1: ('vienas',),
    2: ('du',),
    3: ('trys',),
    4: ('keturi',),
    5: ('penki',),
    6: ('šeši',),
    7: ('septyni',),
    8: ('aštuoni',),
    9: ('devyni',),
}

TENS = {
    0: ('dešimt',),
    1: ('vienuolika',),
    2: ('dvylika',),
    3: ('trylika',),
    4: ('keturiolika',),
    5: ('penkiolika',),
    6: ('šešiolika',),
    7: ('septyniolika',),
    8: ('aštuoniolika',),
    9: ('devyniolika',),
}

TWENTIES = {
    2: ('dvidešimt',),
    3: ('trisdešimt',),
    4: ('keturiasdešimt',),
    5: ('penkiasdešimt',),
    6: ('šešiasdešimt',),
    7: ('septyniasdešimt',),
    8: ('aštuoniasdešimt',),
    9: ('devyniasdešimt',),
}

HUNDRED = ('šimtas', 'šimtai')

THOUSANDS = {
    1: ('tūkstantis', 'tūkstančiai', 'tūkstančių'),
    2: ('milijonas', 'milijonai', 'milijonų'),
    3: ('milijardas', 'milijardai', 'milijardų'),
    4: ('trilijonas', 'trilijonai', 'trilijonų'),
    5: ('kvadrilijonas', 'kvadrilijonai', 'kvadrilijonų'),
    6: ('kvintilijonas', 'kvintilijonai', 'kvintilijonų'),
    7: ('sikstilijonas', 'sikstilijonai', 'sikstilijonų'),
    8: ('septilijonas', 'septilijonai', 'septilijonų'),
    9: ('oktilijonas', 'oktilijonai', 'oktilijonų'),
    10: ('naintilijonas', 'naintilijonai', 'naintilijonų'),
}

GENERIC_CENTS = ('centas', 'centai', 'centų')


class Num2Word_LT(Num2Word_Base):
    CURRENCY_FORMS = {
        'LTL': (('litas', 'litai', 'litų'), GENERIC_CENTS),
        'EUR': (('euras', 'eurai', 'eurų'), GENERIC_CENTS),
        'USD': (('doleris', 'doleriai', 'dolerių'), GENERIC_CENTS),
        'GBP': (
            ('svaras sterlingų', 'svarai sterlingų', 'svarų sterlingų'),
            ('pensas', 'pensai', 'pensų')
        ),
        'PLN': (
            ('zlotas', 'zlotai', 'zlotų'),
            ('grašis', 'grašiai', 'grašių')),
        'RUB': (
            ('rublis', 'rubliai', 'rublių'),
            ('kapeika', 'kapeikos', 'kapeikų')
        ),
    }

    def setup(self):
        self.negword = "minus"
        self.pointword = "kablelis"

    def pluralize(self, n, forms):
        n1, n2, n3 = get_digits(n)
        if n2 == 1 or n1 == 0 or n == 0:
            return forms[2]
        elif n1 == 1:
            return forms[0]
        else:
            return forms[1]

    def to_cardinal(self, number):
        n = str(number).replace(',', '.')
        base_str, n = self.parse_minus(n)
        if '.' in n:
            left, right = n.split('.')
            leading_zero_count = len(right) - len(right.lstrip('0'))
            decimal_part = ((ZERO[0] + ' ') * leading_zero_count +
                            self._int2word(int(right)))
            return '%s%s %s %s' % (
                base_str,
                self._int2word(int(left)),
                self.pointword,
                decimal_part
            )
        else:
            return "%s%s" % (base_str, self._int2word(int(n)))

    def to_ordinal(self, number):
        raise NotImplementedError()

    def _cents_verbose(self, number, currency):
        return self._int2word(number, currency == 'RUB')

    def _int2word(self, n, feminine=False):
        if n == 0:
            return ZERO[0]

        words = []
        chunks = list(splitbyx(str(n), 3))
        i = len(chunks)

        for x in chunks:
            i -= 1

            if x == 0:
                continue

            n1, n2, n3 = get_digits(x)

            if n3 > 0:
                words.append(ONES[n3][0])
                if n3 > 1:
                    words.append(HUNDRED[1])
                else:
                    words.append(HUNDRED[0])

            if n2 > 1:
                words.append(TWENTIES[n2][0])

            if n2 == 1:
                words.append(TENS[n1][0])
            elif n1 > 0:
                if (i == 1 or feminine and i == 0) and n < 1000:
                    words.append(ONES_FEMININE[n1][0])
                else:
                    words.append(ONES[n1][0])

            if i > 0:
                words.append(self.pluralize(x, THOUSANDS[i]))

        return ' '.join(words)
