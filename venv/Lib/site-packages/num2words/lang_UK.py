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

ZERO = ('нуль',)

ONES_FEMININE = {
    1: ('одна',),
    2: ('двi',),
    3: ('три',),
    4: ('чотири',),
    5: ('п\'ять',),
    6: ('шiсть',),
    7: ('сiм',),
    8: ('вiсiм',),
    9: ('дев\'ять',),
}

ONES = {
    1: ('один',),
    2: ('два',),
    3: ('три',),
    4: ('чотири',),
    5: ('п\'ять',),
    6: ('шiсть',),
    7: ('сiм',),
    8: ('вiсiм',),
    9: ('дев\'ять',),
}

TENS = {
    0: ('десять',),
    1: ('одинадцять',),
    2: ('дванадцять',),
    3: ('тринадцять',),
    4: ('чотирнадцять',),
    5: ('п\'ятнадцять',),
    6: ('шiстнадцять',),
    7: ('сiмнадцять',),
    8: ('вiсiмнадцять',),
    9: ('дев\'ятнадцять',),
}

TWENTIES = {
    2: ('двадцять',),
    3: ('тридцять',),
    4: ('сорок',),
    5: ('п\'ятдесят',),
    6: ('шiстдесят',),
    7: ('сiмдесят',),
    8: ('вiсiмдесят',),
    9: ('дев\'яносто',),
}

HUNDREDS = {
    1: ('сто',),
    2: ('двiстi',),
    3: ('триста',),
    4: ('чотириста',),
    5: ('п\'ятсот',),
    6: ('шiстсот',),
    7: ('сiмсот',),
    8: ('вiсiмсот',),
    9: ('дев\'ятсот',),
}

THOUSANDS = {
    1: ('тисяча', 'тисячi', 'тисяч'),  # 10^3
    2: ('мiльйон', 'мiльйони', 'мiльйонiв'),  # 10^6
    3: ('мiльярд', 'мiльярди', 'мiльярдiв'),  # 10^9
    4: ('трильйон', 'трильйони', 'трильйонiв'),  # 10^12
    5: ('квадрильйон', 'квадрильйони', 'квадрильйонiв'),  # 10^15
    6: ('квiнтильйон', 'квiнтильйони', 'квiнтильйонiв'),  # 10^18
    7: ('секстильйон', 'секстильйони', 'секстильйонiв'),  # 10^21
    8: ('септильйон', 'септильйони', 'септильйонiв'),  # 10^24
    9: ('октильйон', 'октильйони', 'октильйонiв'),  # 10^27
    10: ('нонiльйон', 'нонiльйони', 'нонiльйонiв'),  # 10^30
}


class Num2Word_UK(Num2Word_Base):
    CURRENCY_FORMS = {
        'UAH': (
            ('гривня', 'гривнi', 'гривень'),
            ('копiйка', 'копiйки', 'копiйок')
        ),
        'EUR': (
            ('євро', 'євро', 'євро'), ('цент', 'центи', 'центiв')
        ),
    }

    def setup(self):
        self.negword = "мiнус"
        self.pointword = "кома"

    def to_cardinal(self, number):
        n = str(number).replace(',', '.')
        if '.' in n:
            left, right = n.split('.')
            return '%s %s %s' % (
                self._int2word(int(left)),
                self.pointword,
                self._int2word(int(right))
            )
        else:
            return self._int2word(int(n))

    def pluralize(self, n, forms):
        if n % 100 < 10 or n % 100 > 20:
            if n % 10 == 1:
                form = 0
            elif 5 > n % 10 > 1:
                form = 1
            else:
                form = 2
        else:
            form = 2

        return forms[form]

    def _int2word(self, n, feminine=True):
        if n < 0:
            return ' '.join([self.negword, self._int2word(abs(n))])

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
            # elif n1 > 0 and not (i > 0 and x == 1):
            elif n1 > 0:
                ones = ONES_FEMININE if i == 1 or feminine and i == 0 else ONES
                words.append(ones[n1][0])

            if i > 0:
                words.append(self.pluralize(x, THOUSANDS[i]))

        return ' '.join(words)

    def _cents_verbose(self, number, currency):
        return self._int2word(number, currency == 'UAH')

    def to_ordinal(self, number):
        raise NotImplementedError()
