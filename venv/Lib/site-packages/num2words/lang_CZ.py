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

ZERO = ('nula',)

ONES = {
    1: ('jedna',),
    2: ('dva',),
    3: ('tři',),
    4: ('čtyři',),
    5: ('pět',),
    6: ('šest',),
    7: ('sedm',),
    8: ('osm',),
    9: ('devět',),
}

TENS = {
    0: ('deset',),
    1: ('jedenáct',),
    2: ('dvanáct',),
    3: ('třináct',),
    4: ('čtrnáct',),
    5: ('patnáct',),
    6: ('šestnáct',),
    7: ('sedmnáct',),
    8: ('osmnáct',),
    9: ('devatenáct',),
}

TWENTIES = {
    2: ('dvacet',),
    3: ('třicet',),
    4: ('čtyřicet',),
    5: ('padesát',),
    6: ('šedesát',),
    7: ('sedmdesát',),
    8: ('osmdesát',),
    9: ('devadesát',),
}

HUNDREDS = {
    1: ('sto',),
    2: ('dvěstě',),
    3: ('třista',),
    4: ('čtyřista',),
    5: ('pětset',),
    6: ('šestset',),
    7: ('sedmset',),
    8: ('osmset',),
    9: ('devětset',),
}

THOUSANDS = {
    1: ('tisíc', 'tisíce', 'tisíc'),  # 10^3
    2: ('milion', 'miliony', 'milionů'),  # 10^6
    3: ('miliarda', 'miliardy', 'miliard'),  # 10^9
    4: ('bilion', 'biliony', 'bilionů'),  # 10^12
    5: ('biliarda', 'biliardy', 'biliard'),  # 10^15
    6: ('trilion', 'triliony', 'trilionů'),  # 10^18
    7: ('triliarda', 'triliardy', 'triliard'),  # 10^21
    8: ('kvadrilion', 'kvadriliony', 'kvadrilionů'),  # 10^24
    9: ('kvadriliarda', 'kvadriliardy', 'kvadriliard'),  # 10^27
    10: ('quintillion', 'quintilliony', 'quintillionů'),  # 10^30
}


class Num2Word_CZ(Num2Word_Base):
    CURRENCY_FORMS = {
        'CZK': (
            ('koruna', 'koruny', 'korun'), ('halíř', 'halíře', 'haléřů')
        ),
        'EUR': (
            ('euro', 'euro', 'euro'), ('cent', 'centy', 'centů')
        ),
    }

    def setup(self):
        self.negword = "mínus"
        self.pointword = "celá"

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
