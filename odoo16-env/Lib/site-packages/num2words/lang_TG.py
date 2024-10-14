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

GENERIC_DOLLARS = ("доллар", "доллар")
GENERIC_CENTS = ("сент", "сент")


class Num2Word_TG(lang_EU.Num2Word_EU):
    CURRENCY_FORMS = {
        # repalced by EUR
        "EUR": (("евро", "евро"), GENERIC_CENTS),
        # replaced by EUR
        "USD": (GENERIC_DOLLARS, GENERIC_CENTS),
        "RUB": (("рубл", "рубл"), ("копейк", "копейк")),
        "TJS": (("сомонӣ", "сомонӣ"), ("дирам", "дирам")),
    }

    GIGA_SUFFIX = "иллиард"
    MEGA_SUFFIX = "иллион"

    def set_high_numwords(self, high):
        cap = 3 * (len(high) + 1)

        for word, n in zip(high, range(cap, 5, -3)):
            if n == 9:
                self.cards[10 ** n] = word + self.GIGA_SUFFIX

            else:
                self.cards[10 ** n] = word + self.MEGA_SUFFIX

    def setup(self):
        super(Num2Word_TG, self).setup()

        lows = ["квинт", "квадр", "тр", "м", "м"]
        self.high_numwords = self.gen_high_numwords([], [], lows)
        self.negword = "минус "
        self.pointword = "нуқта"
        self.exclude_title = ["ва", "минус", "нуқта"]

        self.mid_numwords = [
            (1000, "ҳазор"),
            (100, "сад"),
            (90, "навад"),
            (80, "ҳаштод"),
            (70, "ҳафтод"),
            (60, "шаст"),
            (50, "панҷоҳ"),
            (40, "чил"),
            (30, "си"),
        ]
        self.low_numwords = [
            "бист",
            "нуздаҳ",
            "ҳаждаҳ",
            "ҳабдаҳ",
            "шонздаҳ",
            "понздаҳ",
            "чордаҳ",
            "сенздаҳ",
            "дувоздаҳ",
            "ёздаҳ",
            "даҳ",
            "нӯҳ",
            "ҳашт",
            "ҳафт",
            "шаш",
            "панҷ",
            "чор",
            "се",
            "ду",
            "як",
            "сифр",
        ]

    def to_cardinal(self, value):
        try:
            assert int(value) == value
        except (ValueError, TypeError, AssertionError):
            return self.to_cardinal_float(value)

        out = ""
        if value < 0:
            value = abs(value)
            out = self.negword

        if value >= self.MAXVAL:
            raise OverflowError(self.errmsg_toobig % (value, self.MAXVAL))

        if value == 100:
            return self.title(out + "сад")
        else:
            val = self.splitnum(value)
            words, num = self.clean(val)
            return self.title(out + words)

    def merge(self, lpair, rpair):
        ltext, lnum = lpair
        rtext, rnum = rpair
        if lnum == 1 and rnum < 100:
            return (rtext, rnum)
        elif 100 > lnum > rnum:
            if ltext == "си":
                return ("%sю %s" % (ltext, rtext), lnum + rnum)
            elif ltext == "панҷоҳ":
                return ("панҷову %s" % (rtext), lnum + rnum)
            else:
                return ("%sу %s" % (ltext, rtext), lnum + rnum)
        elif lnum >= 100 > rnum:
            return ("%sу %s" % (ltext, rtext), lnum + rnum)
        elif rnum > lnum:
            if ltext == "яксад" and rtext not in self.low_numwords:
                return ("сад %s" % (rtext), lnum * rnum)
            if rtext == "сад":
                return ("%s%s" % (ltext, rtext), lnum * rnum)
            else:
                return ("%s %s" % (ltext, rtext), lnum * rnum)
        return ("%sу %s" % (ltext, rtext), lnum + rnum)

    def to_ordinal(self, value):
        self.verify_ordinal(value)
        cardinal = self.to_cardinal(value)
        outwords = cardinal.split(" ")
        lastword = outwords[-1]
        if lastword in ["ду", "се", "си"]:
            return "%sюм" % (cardinal)
        else:
            return "%sум" % (cardinal)

    def to_ordinal_num(self, value):
        self.verify_ordinal(value)
        return "%s%s" % (value, self.to_ordinal(value)[-2:])
