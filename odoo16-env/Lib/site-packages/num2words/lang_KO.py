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

from .base import Num2Word_Base
from .currency import parse_currency_parts


class Num2Word_KO(Num2Word_Base):
    CURRENCY_FORMS = {
        'KRW': ('원', None),
        'USD': ('달러', '센트'),
        'JPY': ('엔', None)
    }

    def set_high_numwords(self, high):
        max = 4 * len(high)
        for word, n in zip(high, range(max, 0, -4)):
            self.cards[10 ** n] = word

    def setup(self):
        super(Num2Word_KO, self).setup()

        self.negword = "마이너스 "
        self.pointword = "점"

        self.high_numwords = [
            '무량대수',
            '불가사의',
            '나유타',
            '아승기',
            '항하사',
            '극',
            '재',
            '정',
            '간',
            '구',
            '양',
            '자',
            '해',
            '경',
            '조',
            '억',
            '만']
        self.mid_numwords = [(1000, "천"), (100, "백")]
        self.low_numwords = ["십", "구", "팔", "칠", "육", "오", "사", "삼", "이",
                             "일", "영"]
        self.ords = {"일": "한",
                     "이": "두",
                     "삼": "세",
                     "사": "네",
                     "오": "다섯",
                     "육": "여섯",
                     "칠": "일곱",
                     "팔": "여덟",
                     "구": "아홉",
                     "십": "열",
                     "이십": "스물",
                     "삼십": "서른",
                     "사십": "마흔",
                     "오십": "쉰",
                     "육십": "예순",
                     "칠십": "일흔",
                     "팔십": "여든",
                     "구십": "아흔"}

    def merge(self, lpair, rpair):
        ltext, lnum = lpair
        rtext, rnum = rpair
        if lnum == 1 and rnum <= 10000:
            return rpair
        elif 10000 > lnum > rnum:
            return ("%s%s" % (ltext, rtext), lnum + rnum)
        elif lnum >= 10000 and lnum > rnum:
            return ("%s %s" % (ltext, rtext), lnum + rnum)
        else:
            return ("%s%s" % (ltext, rtext), lnum * rnum)

    def to_ordinal(self, value):
        self.verify_ordinal(value)
        if value == 1:
            return "첫 번째"
        outwords = self.to_cardinal(value).split(" ")
        lastwords = outwords[-1].split("백")
        if "십" in lastwords[-1]:
            ten_one = lastwords[-1].split("십")
            ten_one[0] = self.ords[ten_one[0] + "십"]
            try:
                ten_one[1] = self.ords[ten_one[1]]
                ten_one[0] = ten_one[0].replace("스무", "스물")
            except KeyError:
                pass
            lastwords[-1] = ''.join(ten_one)
        else:
            lastwords[-1] = self.ords[lastwords[-1]]
        outwords[-1] = "백 ".join(lastwords)
        return " ".join(outwords) + " 번째"

    def to_ordinal_num(self, value):
        self.verify_ordinal(value)
        return "%s 번째" % (value)

    def to_year(self, val, suffix=None, longval=True):
        if val < 0:
            val = abs(val)
            suffix = '기원전' if not suffix else suffix
        valtext = self.to_cardinal(val)
        return ("%s년" % valtext if not suffix
                else "%s %s년" % (suffix, valtext))

    def to_currency(self, val, currency="KRW", cents=False, separator="",
                    adjective=False):
        left, right, is_negative = parse_currency_parts(
            val, is_int_with_cents=cents)

        try:
            cr1, cr2 = self.CURRENCY_FORMS[currency]
            if (cents or right) and not cr2:
                raise ValueError('Decimals not supported for "%s"' % currency)
        except KeyError:
            raise NotImplementedError(
                'Currency code "%s" not implemented for "%s"' %
                (currency, self.__class__.__name__))

        minus_str = self.negword if is_negative else ""
        return '%s%s%s%s%s' % (
            minus_str,
            ''.join(self.to_cardinal(left).split()),
            cr1,
            ' ' + self.to_cardinal(right)
            if cr2 else '',
            cr2 if cr2 else '',
        )
