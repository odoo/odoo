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


class Num2Word_AM(lang_EU.Num2Word_EU):
    CURRENCY_FORMS = {'ETB': (('ብር', 'ብር'), ('ሳንቲም', 'ሳንቲም'))}

    GIGA_SUFFIX = 'ቢሊዮን'
    MEGA_SUFFIX = 'ሚሊዮን'

    def set_high_numwords(self, high):
        cap = 3 * (len(high) + 1)

        for word, n in zip(high, range(cap, 5, -3)):
            if n == 9:
                self.cards[10 ** n] = word + self.GIGA_SUFFIX
            else:
                self.cards[10 ** n] = word + self.MEGA_SUFFIX

    def setup(self):
        super(Num2Word_AM, self).setup()

        self.negword = 'አሉታዊ '
        self.pointword = 'ነጥብ'
        self.exclude_title = ['እና', 'ነጥብ', 'አሉታዊ']

        self.mid_numwords = [(1000, 'ሺህ'), (100, 'መቶ'), (90, 'ዘጠና'),
                             (80, 'ሰማኒያ'), (70, 'ሰባ'), (60, 'ስድሳ'),
                             (50, 'አምሳ'), (40, 'አርባ'), (30, 'ሠላሳ')]
        self.low_numwords = ['ሃያ', 'አሥራ ዘጠኝ', 'አሥራ ስምንት', 'አሥራ ሰባት',
                             'አስራ ስድስት', 'አሥራ አምስት', 'አሥራ አራት', 'አሥራ ሦስት',
                             'አሥራ ሁለት', 'አሥራ አንድ', 'አሥር', 'ዘጠኝ', 'ስምንት',
                             'ሰባት', 'ስድስት', 'አምስት', 'አራት', 'ሦስት', 'ሁለት',
                             'አንድ', 'ዜሮ']
        self.ords = {'አንድ': 'አንደኛ',
                     'ሁለት': 'ሁለተኛ',
                     'ሦስት': 'ሦስተኛ',
                     'አራት': 'አራተኛ',
                     'አምስት': 'አምስተኛ',
                     'ስድስት': 'ስድስተኛ',
                     'ሰባት': 'ሰባተኛ',
                     'ስምንት': 'ስምንተኛ',
                     'ዘጠኝ': 'ዘጠነኛ',
                     'አሥር': 'አሥረኛ',
                     'አሥራ አንድ': 'አሥራ አንደኛ',
                     'አሥራ ሁለት': 'አሥራ ሁለተኛ',
                     'አሥራ ሦስት': 'አሥራ ሦስተኛ',
                     'አሥራ አራት': 'አሥራ አራተኛ',
                     'አሥራ አምስት': 'አሥራ አምስተኛ',
                     'አሥራ ስድስት': 'አሥራ ስድስተኛ',
                     'አሥራ ሰባት': 'አሥራ ሰባተኛ',
                     'አሥራ ስምንት': 'አሥራ ስምንተኛ',
                     'አሥራ ዘጠኝ': 'አሥራ ዘጠነኛ'}

    def to_cardinal(self, value):
        try:
            assert int(value) == value
        except (ValueError, TypeError, AssertionError):
            return self.to_cardinal_float(value)

        out = ''
        if value >= self.MAXVAL:
            raise OverflowError(self.errmsg_toobig % (value, self.MAXVAL))

        if value == 100:
            return self.title(out + 'መቶ')
        else:
            val = self.splitnum(value)
            words, num = self.clean(val)
            return self.title(out + words)

    def merge(self, lpair, rpair):
        ltext, lnum = lpair
        rtext, rnum = rpair
        if lnum == 1 and rnum < 100:
            return rtext, rnum
        elif 100 > lnum > rnum:
            return '%s %s' % (ltext, rtext), lnum + rnum
        elif lnum >= 100 > rnum:
            return '%s %s' % (ltext, rtext), lnum + rnum
        elif rnum > lnum:
            return '%s %s' % (ltext, rtext), lnum * rnum

    def to_ordinal(self, value):
        self.verify_ordinal(value)
        outwords = self.to_cardinal(value).split(' ')
        lastwords = outwords[-1].split('-')
        lastword = lastwords[-1].lower()
        try:
            lastword = self.ords[lastword]
        except KeyError:
            lastword += 'ኛ'
        lastwords[-1] = self.title(lastword)
        outwords[-1] = ' '.join(lastwords)
        return ' '.join(outwords)

    def to_ordinal_num(self, value):
        self.verify_ordinal(value)
        return '%s%s' % (value, self.to_ordinal(value)[-1:])

    def to_currency(self, val, currency='ብር', cents=True, separator=' ከ',
                    adjective=True):
        result = super(Num2Word_AM, self).to_currency(
            val, currency=currency, cents=cents, separator=separator,
            adjective=adjective)
        return result

    def to_year(self, val, longval=True):
        if not (val // 100) % 10:
            return self.to_cardinal(val)
        return self.to_splitnum(val, hightxt='መቶ', longval=longval)
