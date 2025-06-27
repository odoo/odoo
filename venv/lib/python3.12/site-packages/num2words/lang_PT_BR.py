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
from __future__ import division, unicode_literals

import re

from . import lang_PT


class Num2Word_PT_BR(lang_PT.Num2Word_PT):
    def set_high_numwords(self, high):
        max = 3 + 3*len(high)
        for word, n in zip(high, range(max, 3, -3)):
            self.cards[10**n] = word + "ilhão"

    def setup(self):
        super(Num2Word_PT_BR, self).setup()

        self.low_numwords[1] = 'dezenove'
        self.low_numwords[3] = 'dezessete'
        self.low_numwords[4] = 'dezesseis'

        self.thousand_separators = {
            3: "milésimo",
            6: "milionésimo",
            9: "bilionésimo",
            12: "trilionésimo",
            15: "quadrilionésimo"
        }

    def merge(self, curr, next):
        ctext, cnum, ntext, nnum = curr + next

        if cnum == 1:
            if nnum < 1000000:
                return next
            ctext = "um"
        elif cnum == 100 and nnum % 1000 != 0:
            ctext = "cento"

        if nnum < cnum:
            if cnum < 100:
                return ("%s e %s" % (ctext, ntext), cnum + nnum)
            return ("%s e %s" % (ctext, ntext), cnum + nnum)

        elif (not nnum % 1000000) and cnum > 1:
            ntext = ntext[:-4] + "lhões"

        if nnum == 100:
            ctext = self.hundreds[cnum]
            ntext = ""

        else:
            ntext = " " + ntext

        return (ctext + ntext, cnum * nnum)

    def to_cardinal(self, value):
        result = lang_PT.Num2Word_EU.to_cardinal(self, value)

        # Transforms "mil E cento e catorze reais" into "mil, cento e catorze
        # reais"
        for ext in (
                'mil', 'milhão', 'milhões', 'bilhão', 'bilhões',
                'trilhão', 'trilhões', 'quatrilhão', 'quatrilhões'):
            if re.match('.*{} e \\w*entos? (?=.*e)'.format(ext), result):
                result = result.replace(
                    '{} e'.format(ext), '{},'.format(ext), 1
                )

        return result

    def to_currency(self, val, longval=True):
        integer_part, decimal_part = ('%.2f' % val).split('.')

        result = self.to_cardinal(int(integer_part))

        appended_currency = False
        for ext in (
                'milhão', 'milhões', 'bilhão', 'bilhões',
                'trilhão', 'trilhões', 'quatrilhão', 'quatrilhões'):
            if result.endswith(ext):
                result += ' de reais'
                appended_currency = True

        if result in ['um', 'menos um']:
            result += ' real'
            appended_currency = True
        if not appended_currency:
            result += ' reais'

        if int(decimal_part):
            cents = self.to_cardinal(int(decimal_part))
            result += ' e ' + cents

            if cents == 'um':
                result += ' centavo'
            else:
                result += ' centavos'

        return result
