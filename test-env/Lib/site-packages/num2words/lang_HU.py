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

from __future__ import division, print_function, unicode_literals

from . import lang_EU

ZERO = 'nulla'


class Num2Word_HU(lang_EU.Num2Word_EU):
    GIGA_SUFFIX = "illiárd"
    MEGA_SUFFIX = "illió"

    def setup(self):
        super(Num2Word_HU, self).setup()

        self.negword = "mínusz "
        self.pointword = "egész"

        self.mid_numwords = [(1000, "ezer"), (100, "száz"), (90, "kilencven"),
                             (80, "nyolcvan"), (70, "hetven"), (60, "hatvan"),
                             (50, "ötven"), (40, "negyven"), (30, "harminc")]

        low_numwords = ["kilenc", "nyolc", "hét", "hat", "öt", "négy", "három",
                        "kettő", "egy"]
        self.low_numwords = (['tizen' + w for w in low_numwords]
                             + ['tíz']
                             + low_numwords)
        self.low_numwords = (['huszon' + w for w in low_numwords]
                             + ['húsz']
                             + self.low_numwords
                             + [ZERO])

        self.partial_ords = {
            'nulla': 'nullad',
            'egy': 'egyed',
            'kettő': 'ketted',
            'három': 'harmad',
            'négy': 'negyed',
            'öt': 'ötöd',
            'hat': 'hatod',
            'hét': 'heted',
            'nyolc': 'nyolcad',
            'kilenc': 'kilenced',
            'tíz': 'tized',
            'húsz': 'huszad',
            'harminc': 'harmincad',
            'negyven': 'negyvened',
            'ötven': 'ötvened',
            'hatvan': 'hatvanad',
            'hetven': 'hetvened',
            'nyolcvan': 'nyolcvanad',
            'kilencven': 'kilencvened',
            'száz': 'század',
            'ezer': 'ezred',
            'illió': 'milliomod',
            'illiárd': 'milliárdod'
        }

    def to_cardinal(self, value, zero=ZERO):
        if int(value) != value:
            return self.to_cardinal_float(value)
        elif value < 0:
            out = self.negword + self.to_cardinal(-value)
        elif value == 0:
            out = zero
        elif zero == '' and value == 2:
            out = 'két'
        elif value < 30:
            out = self.cards[value]
        elif value < 100:
            out = self.tens_to_cardinal(value)
        elif value < 1000:
            out = self.hundreds_to_cardinal(value)
        elif value < 10**6:
            out = self.thousands_to_cardinal(value)
        else:
            out = self.big_number_to_cardinal(value)
        return out

    def tens_to_cardinal(self, value):
        try:
            return self.cards[value]
        except KeyError:
            return self.cards[value // 10 * 10] + self.to_cardinal(value % 10)

    def hundreds_to_cardinal(self, value):
        hundreds = value // 100
        prefix = "száz"
        if hundreds != 1:
            prefix = self.to_cardinal(hundreds, zero="") + prefix
        postfix = self.to_cardinal(value % 100, zero="")
        return prefix + postfix

    def thousands_to_cardinal(self, value):
        thousands = value // 1000
        prefix = "ezer"
        if thousands != 1:
            prefix = self.to_cardinal(thousands, zero="") + prefix
        postfix = self.to_cardinal(value % 1000, zero="")
        return prefix + ('' if value <= 2000 or not postfix else '-') + postfix

    def big_number_to_cardinal(self, value):
        digits = len(str(value))
        digits = digits if digits % 3 != 0 else digits - 2
        exp = 10 ** (digits // 3 * 3)
        rest = self.to_cardinal(value % exp, '')
        return (self.to_cardinal(value // exp, '') + self.cards[exp]
                + ('-' + rest if rest else ''))

    def to_ordinal(self, value):
        if value < 0:
            return self.negword + self.to_ordinal(-value)
        if value == 1:
            return 'első'
        elif value == 2:
            return 'második'
        else:
            out = self.to_cardinal(value)
            for card_word, ord_word in self.partial_ords.items():
                if out[-len(card_word):] == card_word:
                    out = out[:-len(card_word)] + ord_word
                    break
        return out + 'ik'

    def to_ordinal_num(self, value):
        self.verify_ordinal(value)
        return str(value) + '.'

    def to_year(self, val, suffix=None, longval=True):
        # suffix is prefix here
        prefix = ''
        if val < 0 or suffix is not None:
            val = abs(val)
            prefix = (suffix + ' ' if suffix is not None else 'i. e. ')
        return prefix + self.to_cardinal(val)

    def to_currency(self, val, currency='HUF', cents=True, separator=',',
                    adjective=False):
        return super(Num2Word_HU, self).to_currency(
            val, currency, cents, separator, adjective)

    def to_cardinal_float(self, value):
        if abs(value) != value:
            return self.negword + self.to_cardinal_float(-value)
        left, right = str(value).split('.')
        return (self.to_cardinal(int(left))
                + ' egész '
                + self.to_cardinal(int(right))
                + ' ' + self.partial_ords[self.cards[10 ** len(right)]])
