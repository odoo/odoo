# -*- coding: utf-8 -*-
# Copyright (c) 2021, Savoir-faire Linux inc.  All Rights Reserved.

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

from __future__ import print_function, unicode_literals

from .base import Num2Word_Base


class Num2Word_EO(Num2Word_Base):
    CURRENCY_FORMS = {
        "EUR": (("eŭro", "eŭroj"), ("centimo", "centimoj")),
        "USD": (("dolaro", "dolaroj"), ("cendo", "cendoj")),
        "FRF": (("franko", "frankoj"), ("centimo", "centimoj")),
        "GBP": (("pundo", "pundoj"), ("penco", "pencoj")),
        "CNY": (("juano", "juanoj"), ("feno", "fenoj")),
    }

    GIGA_SUFFIX = "iliardo"
    MEGA_SUFFIX = "iliono"

    def set_high_numwords(self, high):
        cap = 3 + 6 * len(high)

        for word, n in zip(high, range(cap, 3, -6)):
            if self.GIGA_SUFFIX:
                self.cards[10 ** n] = word + self.GIGA_SUFFIX

            if self.MEGA_SUFFIX:
                self.cards[10 ** (n - 3)] = word + self.MEGA_SUFFIX

    def gen_high_numwords(self, units, tens, lows):
        out = [u + t for t in tens for u in units]
        out.reverse()
        return out + lows

    def setup(self):
        lows = ["naŭ", "ok", "sep", "ses", "kvin", "kvar", "tr", "b", "m"]
        units = ["", "un", "duo", "tre", "kvatuor",
                 "kvin", "seks", "septen", "okto", "novem"]
        tens = ["dek", "vigint", "trigint", "kvadragint", "kvinkvagint",
                "seksagint", "septuagint", "oktogint", "nonagint"]

        self.high_numwords = ["cent"] + self.gen_high_numwords(units, tens,
                                                               lows)

        self.negword = "minus "
        self.pointword = "komo"
        self.errmsg_nonnum = u"Sole nombroj povas esti konvertita en vortojn."
        self.errmsg_toobig = (
            u"Tro granda nombro por esti konvertita en vortojn (abs(%s) > %s)."
        )
        self.exclude_title = ["kaj", "komo", "minus"]
        self.mid_numwords = [(1000, "mil"), (100, "cent"), (90, "naŭdek"),
                             (80, "okdek"), (70, "sepdek"), (60, "sesdek"),
                             (50, "kvindek"), (40, "kvardek"), (30, "tridek")]
        self.low_numwords = ["dudek", "dek naŭ", "dek ok", "dek sep",
                             "dek ses", "dek kvin", "dek kvar", "dek tri",
                             "dek du", "dek unu", "dek", "naŭ", "ok", "sep",
                             "ses", "kvin", "kvar", "tri", "du", "unu", "nul"]
        self.ords = {
            "unu": "unua",
            "du": "dua",
            "tri": "tria",
            "kvar": "kvara",
            "kvin": "kvina",
            "ses": "sesa",
            "sep": "sepa",
            "ok": "oka",
            "naŭ": "naŭa",
            "dek": "deka"
        }

    def merge(self, curr, next):
        ctext, cnum, ntext, nnum = curr + next
        if cnum == 1 and nnum < 1000000:
            return next

        if nnum >= 10**6 and cnum > 1:
            return ("%s %sj" % (ctext, ntext), cnum + nnum)

        if nnum == 100:
            return ("%s%s" % (ctext, ntext), cnum + nnum)

        return ("%s %s" % (ctext, ntext), cnum + nnum)

    def to_ordinal(self, value):
        self.verify_ordinal(value)
        word = self.to_cardinal(value)
        for src, repl in self.ords.items():
            if word.endswith(src):
                word = word[:-len(src)] + repl
                return word

        if word.endswith("o"):
            word = word[:-1] + "a"
        elif word.endswith("oj"):
            word = word[:-2] + "a"
        else:
            word = word + "a"
        return word

    def to_ordinal_num(self, value):
        self.verify_ordinal(value)
        out = str(value)
        out += "a"
        return out

    def to_currency(self, val, currency="EUR", cents=True, separator=" kaj",
                    adjective=False):
        result = super(Num2Word_EO, self).to_currency(
            val, currency=currency, cents=cents, separator=separator,
            adjective=adjective)
        return result

    def pluralize(self, n, forms):
        form = 0 if n <= 1 else 1
        return forms[form]
