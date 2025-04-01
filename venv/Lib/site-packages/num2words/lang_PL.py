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

ZERO = ('zero',)

ONES = {
    1: ('jeden',),
    2: ('dwa',),
    3: ('trzy',),
    4: ('cztery',),
    5: ('pięć',),
    6: ('sześć',),
    7: ('siedem',),
    8: ('osiem',),
    9: ('dziewięć',),
}

TENS = {
    0: ('dziesięć',),
    1: ('jedenaście',),
    2: ('dwanaście',),
    3: ('trzynaście',),
    4: ('czternaście',),
    5: ('piętnaście',),
    6: ('szesnaście',),
    7: ('siedemnaście',),
    8: ('osiemnaście',),
    9: ('dziewiętnaście',),
}

TWENTIES = {
    2: ('dwadzieścia',),
    3: ('trzydzieści',),
    4: ('czterdzieści',),
    5: ('pięćdziesiąt',),
    6: ('sześćdziesiąt',),
    7: ('siedemdziesiąt',),
    8: ('osiemdziesiąt',),
    9: ('dziewięćdzisiąt',),
}

HUNDREDS = {
    1: ('sto',),
    2: ('dwieście',),
    3: ('trzysta',),
    4: ('czterysta',),
    5: ('pięćset',),
    6: ('sześćset',),
    7: ('siedemset',),
    8: ('osiemset',),
    9: ('dziewięćset',),
}

THOUSANDS = {
    1: ('tysiąc',       'tysiące',      'tysięcy'),        # 10^3
    2: ('milion',       'miliony',      'milionów'),       # 10^6
    3: ('miliard',      'miliardy',     'miliardów'),      # 10^9
    4: ('bilion',       'biliony',      'bilionów'),       # 10^12
    5: ('biliard',      'biliardy',     'biliardów'),      # 10^15
    6: ('trylion',      'tryliony',     'trylionów'),      # 10^18
    7: ('tryliard',     'tryliardy',    'tryliardów'),     # 10^21
    8: ('kwadrylion',   'kwadryliony',  'kwadrylionów'),   # 10^24
    9: ('kwadryliard',  'kwadryliardy', 'kwadryliardów'),  # 10^27
    10: ('kwintylion',  'kwintyliony',  'kwintylionów'),   # 10^30
    11: ('kwintyliard', 'kwintyliardy', 'kwintyliardów'),  # 10^33
    12: ('sekstylion',  'sekstyliony',  'sekstylionów'),   # 10^36
    13: ('sekstyliard', 'sekstyliardy', 'sekstyliardów'),  # 10^39
    14: ('septylion',   'septyliony',   'septylionów'),    # 10^42
    15: ('septyliard',  'septyliardy',  'septyliardów'),   # 10^45
    16: ('oktylion',    'oktyliony',    'oktylionów'),     # 10^48
    17: ('oktyliard',   'oktyliardy',   'oktyliardów'),    # 10^51
    18: ('nonylion',    'nonyliony',    'nonylionów'),     # 10^54
    19: ('nonyliard',   'nonyliardy',   'nonyliardów'),    # 10^57
    20: ('decylion',    'decyliony',    'decylionów'),     # 10^60
    21: ('decyliard',   'decyliardy',   'decyliardów'),    # 10^63
}


class Num2Word_PL(Num2Word_Base):
    CURRENCY_FORMS = {
        'PLN': (
            ('złoty', 'złote', 'złotych'), ('grosz', 'grosze', 'groszy')
        ),
        'EUR': (
            ('euro', 'euro', 'euro'), ('cent', 'centy', 'centów')
        ),
    }

    def setup(self):
        self.negword = "minus"
        self.pointword = "przecinek"

    def to_cardinal(self, number):
        n = str(number).replace(',', '.')
        if '.' in n:
            left, right = n.split('.')
            return u'%s %s %s' % (
                self._int2word(int(left)),
                self.pointword,
                self._int2word(int(right))
            )
        else:
            return self._int2word(int(n))

    def pluralize(self, n, forms):
        if n == 1:
            form = 0
        elif 5 > n % 10 > 1 and (n % 100 < 10 or n % 100 > 20):
            form = 1
        else:
            form = 2
        return forms[form]

    def to_ordinal(self, number):
        raise NotImplementedError()

    def _int2word(self, n):
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
                words.append(HUNDREDS[n3][0])

            if n2 > 1:
                words.append(TWENTIES[n2][0])

            if n2 == 1:
                words.append(TENS[n1][0])
            elif n1 > 0 and not (i > 0 and x == 1):
                words.append(ONES[n1][0])

            if i > 0:
                words.append(self.pluralize(x, THOUSANDS[i]))

        return ' '.join(words)
