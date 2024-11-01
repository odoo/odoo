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

# Genders
KK = 0  # Karlkyn (male)
KVK = 1  # Kvenkyn (female)
HK = 2  # Hvorugkyn (neuter)

GENDERS = {
    "einn": ("einn", "ein", "eitt"),
    "tveir": ("tveir", "tvær", "tvö"),
    "þrír": ("þrír", "þrjár", "þrjú"),
    "fjórir": ("fjórir", "fjórar", "fjögur"),
}

PLURALS = {
    "hundrað": ("hundrað", "hundruð"),
}


class Num2Word_IS(lang_EU.Num2Word_EU):

    GIGA_SUFFIX = "illjarður"
    MEGA_SUFFIX = "illjón"

    def setup(self):
        lows = ["okt", "sept", "sext", "kvint", "kvaðr", "tr", "b", "m"]
        self.high_numwords = self.gen_high_numwords([], [], lows)

        self.negword = "mínus "
        self.pointword = "komma"

        # All words should be excluded, title case is not used in Icelandic
        self.exclude_title = ["og", "komma", "mínus"]

        self.mid_numwords = [(1000, "þúsund"), (100, "hundrað"),
                             (90, "níutíu"), (80, "áttatíu"), (70, "sjötíu"),
                             (60, "sextíu"), (50, "fimmtíu"), (40, "fjörutíu"),
                             (30, "þrjátíu")]
        self.low_numwords = ["tuttugu", "nítján", "átján", "sautján",
                             "sextán", "fimmtán", "fjórtán", "þrettán",
                             "tólf", "ellefu", "tíu", "níu", "átta",
                             "sjö", "sex", "fimm", "fjórir", "þrír",
                             "tveir", "einn", "núll"]
        self.ords = {"einn": "fyrsti",
                     "tveir": "annar",
                     "þrír": "þriðji",
                     "fjórir": "fjórði",
                     "fimm": "fimmti",
                     "sex": "sjötti",
                     "sjö": "sjöundi",
                     "átta": "áttundi",
                     "níu": "níundi",
                     "tíu": "tíundi",
                     "ellefu": "ellefti",
                     "tólf": "tólfti"}

    def pluralize(self, n, noun):
        form = 0 if (n % 10 == 1 and n % 100 != 11) else 1
        if form == 0:
            return noun
        elif self.GIGA_SUFFIX in noun:
            return noun.replace(self.GIGA_SUFFIX, "illjarðar")
        elif self.MEGA_SUFFIX in noun:
            return noun.replace(self.MEGA_SUFFIX, "illjónir")
        elif noun not in PLURALS:
            return noun
        return PLURALS[noun][form]

    def genderize(self, adj, noun):
        last = adj.split()[-1]
        if last not in GENDERS:
            return adj
        gender = KK
        if "hund" in noun or "þús" in noun:
            gender = HK
        elif "illjarð" in noun:
            gender = KK
        elif "illjón" in noun:
            gender = KVK
        return adj.replace(last, GENDERS[last][gender])

    def merge(self, lpair, rpair):
        ltext, lnum = lpair
        rtext, rnum = rpair

        if lnum == 1 and rnum < 100:
            return (rtext, rnum)
        elif lnum < rnum:
            rtext = self.pluralize(lnum, rtext)
            ltext = self.genderize(ltext, rtext)
            return ("%s %s" % (ltext, rtext), lnum * rnum)
        elif lnum > rnum and rnum in self.cards:
            rtext = self.pluralize(lnum, rtext)
            ltext = self.genderize(ltext, rtext)
            return ("%s og %s" % (ltext, rtext), lnum + rnum)
        return ("%s %s" % (ltext, rtext), lnum + rnum)

    def to_ordinal(self, value):
        raise NotImplementedError

    def to_ordinal_num(self, value):
        raise NotImplementedError

    def to_year(self, val, suffix=None, longval=True):
        raise NotImplementedError

    def to_currency(self, val, longval=True):
        raise NotImplementedError
