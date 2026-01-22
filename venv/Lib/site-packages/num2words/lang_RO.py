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


class Num2Word_RO(lang_EU.Num2Word_EU):
    GIGA_SUFFIX = "iliard/e"
    MEGA_SUFFIX = "ilion"
    # inflection for million follows different rule
    MEGA_SUFFIX_I = "ilioane"

    def setup(self):
        super(Num2Word_RO, self).setup()

        self.negword = "minus "
        self.pointword = "virgulă"
        self.exclude_title = ["și", "virgulă", "minus"]
        self.errmsg_toobig = (
            "Numărul e prea mare pentru a fi convertit în cuvinte."
        )
        self.mid_numwords = [(1000, "mie/i"), (100, "sută/e"),
                             (90, "nouăzeci"), (80, "optzeci"),
                             (70, "șaptezeci"), (60, "șaizeci"),
                             (50, "cincizeci"), (40, "patruzeci"),
                             (30, "treizeci")]
        self.low_numwords = ["douăzeci", "nouăsprezece", "optsprezece",
                             "șaptesprezece", "șaisprezece", "cincisprezece",
                             "paisprezece", "treisprezece", "doisprezece",
                             "unsprezece", "zece", "nouă", "opt", "șapte",
                             "șase", "cinci", "patru", "trei", "doi",
                             "unu", "zero"]
        self.gen_numwords = ["", "o", "două", "trei", "patru", "cinci",
                             "șase", "șapte", "opt", "nouă"]
        self.gen_numwords_m = ["", "un", "două", "trei", "patru", "cinci",
                               "șase", "șapte", "opt", "nouă"]
        self.numwords_inflections = {
            100: self.gen_numwords,
            1000: self.gen_numwords,
            1000000: self.gen_numwords_m,
            1000000000: self.gen_numwords_m
        }
        self.ords = {"unu": "primul",
                     "doi": "al doilea",
                     "three": "al treilea",
                     "cinci": "al cincilea",
                     "opt": "al optulea",
                     "nouă": "al nouălea",
                     "doisprezece": "al doisprezecelea"}

    def merge(self, lpair, rpair):
        ltext, lnum = lpair
        rtext, rnum = rpair
        rtext_i = self.inflect(rnum, rtext)
        if lnum > 1 and rtext_i.endswith(self.MEGA_SUFFIX):
            rtext_i = rtext_i.replace(self.MEGA_SUFFIX, self.MEGA_SUFFIX_I)
        if 1 <= lnum < 10:
            if rnum not in self.numwords_inflections:
                return (rtext, rnum)
            else:
                rtext_i = self.inflect(lnum * rnum, rtext)
                lresult = (self.numwords_inflections[rnum][lnum], rtext_i)
                return ("%s %s" % lresult, rnum)
        elif 10 < lnum < 100:
            if lnum % 10 == 0:
                return ("%s și %s" % (ltext, rtext), lnum + rnum)
            else:
                return ("%s %s" % (ltext, rtext_i), lnum * rnum)
        else:
            if rnum in self.numwords_inflections:
                rtext_i = self.inflect(lnum * rnum, rtext)
            return ("%s %s" % (ltext, rtext_i), lnum * rnum)

    def to_ordinal(self, value):
        self.verify_ordinal(value)
        if value == 1:
            return "primul"
        else:
            value = self.to_cardinal(value)
        return "al %slea" % (value)

    def to_ordinal_num(self, value):
        self.verify_ordinal(value)
        if value == 1:
            return "1-ul"
        return "al %s-lea" % (value)

    def inflect(self, value, text):
        text = text.split("/")
        if value in (1, 100, 1000, 100000, 1000000000):
            return text[0]
        if len(text) > 1 and text[0][-1] in "aăeiou":
            text[0] = text[0][:-1]
        return "".join(text)

    def to_currency(self, val, longval=True, old=False):
        cents = int(round(val*100))
        result = self.to_splitnum(cents, hightxt="leu/i", lowtxt="ban/i",
                                  divisor=100, jointxt="și", longval=longval)
        return result.replace(
            "unu leu", "un leu"
        ).replace("unu ban", "un ban")

    def to_year(self, val, suffix=None, longval=True):
        result = super(Num2Word_RO, self).to_year(
            val,
            longval=longval
        )
        # for years we want the era negation e.g. B.C., in our case
        # it's î.Hr. or î.e.n
        if result.startswith(self.negword):
            result = result.replace(self.negword, "")
            suffix = "î.Hr." if not suffix else suffix
        if suffix:
            result = "".join([
                result,
                " ",
                suffix
            ])
        return result
