# -*- coding: utf-8 -*-
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
    1: ('jeden', 'jeden', set()),
    2: ('dva', 'dve', {1, 3, 5, 7, 9}),
    3: ('tri', 'tri', set()),
    4: ('štyri', 'štyri', set()),
    5: ('päť', 'päť', set()),
    6: ('šesť', 'šesť', set()),
    7: ('sedem', 'sedem', set()),
    8: ('osem', 'osem', set()),
    9: ('deväť', 'deväť', set()),
}

TENS = {
    0: ('desať',),
    1: ('jedenásť',),
    2: ('dvanásť',),
    3: ('trinásť',),
    4: ('štrnásť',),
    5: ('pätnásť',),
    6: ('šestnásť',),
    7: ('sedemnásť',),
    8: ('osemnásť',),
    9: ('devätnásť',),
}

TWENTIES = {
    2: ('dvadsať',),
    3: ('tridsať',),
    4: ('štyridsať',),
    5: ('päťdesiat',),
    6: ('šesťdesiat',),
    7: ('sedemdesiat',),
    8: ('osemdesiat',),
    9: ('deväťdesiat',),
}

HUNDREDS = {
    1: ('sto',),
    2: ('dvesto',),
    3: ('tristo',),
    4: ('štyristo',),
    5: ('päťsto',),
    6: ('šesťsto',),
    7: ('sedemsto',),
    8: ('osemsto',),
    9: ('deväťsto',),
}

THOUSANDS = {
    1: ('tisíc', 'tisíc', 'tisíc'),  # 10^3
    2: ('milión', 'milióny', 'miliónov'),  # 10^6
    3: ('miliarda', 'miliardy', 'miliárd'),  # 10^9
    4: ('bilión', 'bilióny', 'biliónov'),  # 10^12
    5: ('biliarda', 'biliardy', 'biliárd'),  # 10^15
    6: ('trilión', 'trilióny', 'triliónov'),  # 10^18
    7: ('triliarda', 'triliardy', 'triliárd'),  # 10^21
    8: ('kvadrilión', 'kvadrilióny', 'kvadriliónov'),  # 10^24
    9: ('kvadriliarda', 'kvadriliardy', 'kvadriliárd'),  # 10^27
    10: ('kvintilión', 'kvintillióny', 'kvintiliónov'),  # 10^30
}


class Num2Word_SK(Num2Word_Base):
    CURRENCY_FORMS = {
        'EUR': (
            ('euro', 'eurá', 'eur'), ('cent', 'centy', 'centov')
        ),
    }

    def setup(self):
        self.negword = "mínus"
        self.pointword = "celých"

    def to_cardinal(self, number):
        n = str(number).replace(',', '.')
        if '.' in n:
            left, right = n.split('.')
            leading_zero_count = len(right) - len(right.lstrip('0'))
            decimal_part = ((ZERO[0] + ' ') * leading_zero_count +
                            self._int2word(int(right)))
            return u'%s %s %s' % (
                self._int2word(int(left)),
                self.pointword,
                decimal_part
            )
        else:
            return self._int2word(int(n))

    def pluralize(self, n, forms):
        if n == 1:
            form = 0
        elif 0 < n < 5:
            form = 1
        else:
            form = 2
        return forms[form]

    def to_ordinal(self, value):
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

            word_chunk = []

            if n3 > 0:
                word_chunk.append(HUNDREDS[n3][0])

            if n2 > 1:
                word_chunk.append(TWENTIES[n2][0])

            if n2 == 1:
                word_chunk.append(TENS[n1][0])
            elif n1 > 0 and not (i > 0 and x == 1):
                if n2 == 0 and n3 == 0 and i in ONES[n1][2]:
                    word_chunk.append(ONES[n1][1])
                else:
                    word_chunk.append(ONES[n1][0])
            if i > 1 and word_chunk:
                word_chunk.append(' ')
            if i > 0:
                word_chunk.append(self.pluralize(x, THOUSANDS[i]))
            words.append(''.join(word_chunk))

        return ' '.join(words[:-1]) + ''.join(words[-1:])
