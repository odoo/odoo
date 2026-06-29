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

import itertools

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

ONES_ORDINALS = {
    1: ('pierwszy', "pierwszo"),
    2: ('drugi', "dwu"),
    3: ('trzeci', "trzy"),
    4: ('czwarty', "cztero"),
    5: ('piąty', "pięcio"),
    6: ('szósty', "sześcio"),
    7: ('siódmy', "siedmio"),
    8: ('ósmy', "ośmio"),
    9: ('dziewiąty', "dziewięcio"),
    10: ('dziesiąty', "dziesięcio"),
    11: ('jedenasty', "jedenasto"),
    12: ('dwunasty', "dwunasto"),
    13: ('trzynasty', "trzynasto"),
    14: ('czternasty', "czternasto"),
    15: ('piętnasty', "piętnasto"),
    16: ('szesnasty', "szesnasto"),
    17: ('siedemnasty', "siedemnasto"),
    18: ('osiemnasty', "osiemnasto"),
    19: ('dziewiętnasty', "dziewiętnasto"),
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
    9: ('dziewięćdziesiąt',),
}

TWENTIES_ORDINALS = {
    2: ('dwudziesty', "dwudziesto"),
    3: ('trzydziesty', "trzydiesto"),
    4: ('czterdziesty', "czterdziesto"),
    5: ('pięćdziesiąty', "pięćdziesięcio"),
    6: ('sześćdziesiąty', "sześćdziesięcio"),
    7: ('siedemdziesiąty', "siedemdziesięcio"),
    8: ('osiemdziesiąty', "osiemdziesięcio"),
    9: ('dziewięćdzisiąty', "dziewięćdziesięcio"),
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

HUNDREDS_ORDINALS = {
    1: ('setny', "stu"),
    2: ('dwusetny', "dwustu"),
    3: ('trzysetny', "trzystu"),
    4: ('czterysetny', "czterystu"),
    5: ('pięćsetny', "pięcset"),
    6: ('sześćsetny', "sześćset"),
    7: ('siedemsetny', "siedemset"),
    8: ('osiemsetny', "ośiemset"),
    9: ('dziewięćsetny', "dziewięćset"),
}

THOUSANDS = {
    1: ('tysiąc', 'tysiące', 'tysięcy'),  # 10^3
}

prefixes_ordinal = {
    1: "tysięczny",
    2: "milionowy",
    3: "milairdowy"
}

prefixes = (   # 10^(6*x)
    "mi",      # 10^6
    "bi",      # 10^12
    "try",     # 10^18
    "kwadry",  # 10^24
    "kwinty",  # 10^30
    "seksty",  # 10^36
    "septy",   # 10^42
    "okty",    # 10^48
    "nony",    # 10^54
    "decy"     # 10^60
)
suffixes = ("lion", "liard")  # 10^x or 10^(x+3)

for idx, (p, s) in enumerate(itertools.product(prefixes, suffixes)):
    name = p + s
    THOUSANDS[idx+2] = (name, name + 'y', name + 'ów')


class Num2Word_PL(Num2Word_Base):
    CURRENCY_FORMS = {
        'PLN': (
            ('złoty', 'złote', 'złotych'), ('grosz', 'grosze', 'groszy')
        ),
        'EUR': (
            ('euro', 'euro', 'euro'), ('cent', 'centy', 'centów')
        ),
        'USD': (
            (
                'dolar amerykański',
                'dolary amerykańskie',
                'dolarów amerykańskich'
            ),
            (
                'cent',
                'centy',
                'centów'
            )
        ),
    }

    def setup(self):
        self.negword = "minus"
        self.pointword = "przecinek"

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
        elif 5 > n % 10 > 1 and (n % 100 < 10 or n % 100 > 20):
            form = 1
        else:
            form = 2
        return forms[form]

    def last_fragment_to_ordinal(self, last, words, level):
        n1, n2, n3 = get_digits(last)
        last_two = n2*10+n1
        if last_two == 0:
            words.append(HUNDREDS_ORDINALS[n3][level])
        elif level == 1 and last == 1:
            return
        elif last_two < 20:
            if n3 > 0:
                words.append(HUNDREDS[n3][level])
            words.append(ONES_ORDINALS[last_two][level])
        elif last_two % 10 == 0:
            if n3 > 0:
                words.append(HUNDREDS[n3][level])
            words.append(TWENTIES_ORDINALS[n2][level])
        else:
            if n3 > 0:
                words.append(HUNDREDS[n3][0])
            words.append(TWENTIES_ORDINALS[n2][0])
            words.append(ONES_ORDINALS[n1][0])

    def to_ordinal(self, number):
        if number % 1 != 0:
            raise NotImplementedError()
        words = []
        fragments = list(splitbyx(str(number), 3))
        level = 0
        last = fragments[-1]
        while last == 0:
            level = level+1
            fragments.pop()
            last = fragments[-1]
        if len(fragments) > 1:
            pre_part = self._int2word(number-(last*1000**level))
            words.append(pre_part)
        self.last_fragment_to_ordinal(last, words, 0 if level == 0 else 1)
        output = " ".join(words)
        if last == 1 and level > 0 and output != "":
            output = output + " "
        if level > 0:
            output = output + prefixes_ordinal[level]
        return output

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
