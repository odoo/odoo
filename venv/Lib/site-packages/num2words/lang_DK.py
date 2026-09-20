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


class Num2Word_DK(lang_EU.Num2Word_EU):
    GIGA_SUFFIX = "illarder"
    MEGA_SUFFIX = "illioner"

    def setup(self):
        super(Num2Word_DK, self).setup()

        self.negword = "minus "
        self.pointword = "komma"
        self.exclude_title = ["og", "komma", "minus"]

        self.mid_numwords = [(1000, "tusind"), (100, "hundrede"),
                             (90, "halvfems"), (80, "firs"),
                             (70, "halvfjerds"), (60, "treds"),
                             (50, "halvtreds"), (40, "fyrre"), (30, "tredive")]
        self.low_numwords = ["tyve", "nitten", "atten", "sytten",
                             "seksten", "femten", "fjorten", "tretten",
                             "tolv", "elleve", "ti", "ni", "otte",
                             "syv", "seks", "fem", "fire", "tre", "to",
                             "et", "nul"]
        self.ords = {"nul": "nul",
                     "et": "f\xf8rste",
                     "to": "anden",
                     "tre": "tredje",
                     "fire": "fjerde",
                     "fem": "femte",
                     "seks": "sjette",
                     "syv": "syvende",
                     "otte": "ottende",
                     "ni": "niende",
                     "ti": "tiende",
                     "elleve": "ellevte",
                     "tolv": "tolvte",
                     "tretten": "trett",
                     "fjorten": "fjort",
                     "femten": "femt",
                     "seksten": "sekst",
                     "sytten": "sytt",
                     "atten": "att",
                     "nitten": "nitt",
                     "tyve": "tyv"}

    def merge(self, curr, next):
        ctext, cnum, ntext, nnum = curr + next
        if next[1] == 100 or next[1] == 1000:
            lst = list(next)
            lst[0] = 'et' + lst[0]
            next = tuple(lst)

        if cnum == 1:
            if nnum < 10 ** 6 or self.ordflag:
                return next
            ctext = "en"
        if nnum > cnum:
            if nnum >= 10 ** 6:
                ctext += " "
            val = cnum * nnum
        else:
            if cnum >= 100 and cnum < 1000:
                ctext += " og "
            elif cnum >= 1000 and cnum <= 100000:
                ctext += "e og "
            if nnum < 10 < cnum < 100:
                if nnum == 1:
                    ntext = "en"
                ntext, ctext = ctext, ntext + "og"
            elif cnum >= 10 ** 6:
                ctext += " "
            val = cnum + nnum
        word = ctext + ntext
        return (word, val)

    def to_ordinal(self, value):
        self.verify_ordinal(value)
        self.ordflag = True
        outword = self.to_cardinal(value)
        self.ordflag = False
        for key in self.ords:
            if outword.endswith(key):
                outword = outword[:len(outword) - len(key)] + self.ords[key]
                break
        if value % 100 >= 30 and value % 100 <= 39 or value % 100 == 0:
            outword += "te"
        elif value % 100 > 12 or value % 100 == 0:
            outword += "ende"
        return outword

    def to_ordinal_num(self, value):
        self.verify_ordinal(value)
        vaerdte = (0, 1, 5, 6, 11, 12)
        if value % 100 >= 30 and value % 100 <= 39 or value % 100 in vaerdte:
            return str(value) + "te"
        elif value % 100 == 2:
            return str(value) + "en"
        return str(value) + "ende"

    def to_currency(self, val, longval=True):
        if val // 100 == 1 or val == 1:
            ret = self.to_splitnum(val, hightxt="kr", lowtxt="\xf8re",
                                   jointxt="og", longval=longval)
            return "en " + ret[3:]
        return self.to_splitnum(val, hightxt="kr", lowtxt="\xf8re",
                                jointxt="og", longval=longval)

    def to_year(self, val, longval=True):
        if val == 1:
            return 'en'
        if not (val // 100) % 10:
            return self.to_cardinal(val)
        return self.to_splitnum(val, hightxt="hundrede", longval=longval)
