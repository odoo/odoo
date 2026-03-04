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
    # inflection for mi/billion follows different rule
    MEGA_SUFFIX_I = "ilioane"
    GIGA_SUFFIX_I = "iliarde"

    def setup(self):
        super(Num2Word_RO, self).setup()

        self.negword = "minus "
        self.pointword = "virgulă"
        self.exclude_title = ["și", "virgulă", "minus"]
        self.errmsg_toobig = (
            "Numărul e prea mare pentru a \
fi convertit în cuvinte (abs(%s) > %s)."
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
        self.gen_numwords_n = ["", "un", "două", "trei", "patru", "cinci",
                               "șase", "șapte", "opt", "nouă"]
        self.numwords_inflections = {
            100: self.gen_numwords,
            1000: self.gen_numwords,
            1000000: self.gen_numwords_n,
            1000000000: self.gen_numwords_n
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
        rtext_i = self.inflect(rnum, rtext, lnum)
        if 1 <= lnum < 10:
            if rnum not in self.numwords_inflections:
                return (rtext, rnum)
            else:
                rtext_i = self.inflect(lnum * rnum, rtext, lnum)
                lresult = (self.numwords_inflections[rnum][lnum], rtext_i)
                return ("%s %s" % lresult, rnum)
        elif 10 < lnum < 100:
            if lnum % 10 == 0:
                if rnum in self.numwords_inflections:
                    rtext_i = self.inflect(lnum * rnum, rtext, lnum)
                    return ("%s %s" % (ltext, rtext_i), lnum * rnum)
                else:
                    return ("%s și %s" % (ltext, rtext), lnum + rnum)
            else:
                rtext_i = self.inflect(lnum * rnum, rtext, lnum)
                ltext_i = ltext if lnum % 10 != 2 \
                    else ltext.replace("doi", "două")
                return ("%s %s" % (ltext_i, rtext_i), lnum * rnum)
        else:
            if rnum in self.numwords_inflections:
                rtext_i = self.inflect(lnum * rnum, rtext, lnum)
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

    def pluralize(self, n, forms):
        if n == 1:
            form = 0
        elif n == 0 or (n % 100 > 0 and n % 100 < 20):
            form = 1
        else:
            form = 2
        return forms[form]

    def inflect(self, value, text, side_effect=-1):
        text = text.split("/")
        result = text[0]
        if len(text) > 1:
            forms = [
                text[0],
                text[0][:-1] + text[1],
                "de " + text[0][:-1] + text[1]
            ]
            result = self.pluralize(side_effect, forms)
        # mega inflections are different
        if side_effect > 1 and result.endswith(self.MEGA_SUFFIX):
            result = result.replace(self.MEGA_SUFFIX, self.MEGA_SUFFIX_I)
        elif side_effect > 1 and result.endswith("iliare"):
            result = result.replace("iliare", self.GIGA_SUFFIX_I)
        return result

    def to_currency(self, val, currency="RON", cents=False, separator=" și",
                    adjective=False):
        # romanian currency has a particularity for numeral: one
        self.gen_numwords[1] = "una"
        result = super(Num2Word_RO, self).to_currency(
            int(round(val*100)),
            currency,
            True,
            separator,
            adjective
        )
        self.gen_numwords[1] = "o"  # revert numeral
        return result.replace(
            "unu leu", "un leu"
        ).replace(
            "unu ban", "un ban"
        ).replace(
            # if the romanian low text is 0, it is not usually printed
            separator + " zero bani", ""
        )

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
