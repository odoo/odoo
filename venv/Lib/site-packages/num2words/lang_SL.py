# -*- coding: utf-8 -*-
# Copyright (c) 2003, Taro Ogawa.  All Rights Reserved.
# Copyright (c) 2013, Savoir-faire Linux inc.  All Rights Reserved.
# Copyright (c) 2015, Blaz Bregar. All Rights Reserved.

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

from __future__ import unicode_literals

from .lang_EU import Num2Word_EU


class Num2Word_SL(Num2Word_EU):
    GIGA_SUFFIX = "ilijard"
    MEGA_SUFFIX = "ilijon"

    def setup(self):
        super(Num2Word_SL, self).setup()

        self.negword = "minus "
        self.pointword = "celih"
        self.errmsg_nonnum = "Only numbers may be converted to words."
        self.errmsg_toobig = "Number is too large to convert to words."
        self.exclude_title = []

        self.mid_numwords = [(1000, "tisoč"), (900, "devetsto"),
                             (800, "osemsto"), (700, "sedemsto"),
                             (600, "šeststo"), (500, "petsto"),
                             (400, "štiristo"), (300, "tristo"),
                             (200, "dvesto"), (100, "sto"),
                             (90, "devetdeset"), (80, "osemdeset"),
                             (70, "sedemdeset"), (60, "šestdeset"),
                             (50, "petdeset"), (40, "štirideset"),
                             (30, "trideset")]
        self.low_numwords = ["dvajset", "devetnajst", "osemnajst",
                             "sedemnajst", "šestnajst", "petnajst",
                             "štirinajst", "trinajst", "dvanajst",
                             "enajst", "deset", "devet", "osem", "sedem",
                             "šest", "pet", "štiri", "tri", "dve", "ena",
                             "nič"]
        self.ords = {"ena": "prv",
                     "dve": "drug",
                     "tri": "tretj",
                     "štiri": "četrt",
                     "sedem": "sedm",
                     "osem": "osm",
                     "sto": "stot",
                     "tisoč": "tisoč",
                     "milijon": "milijont"
                     }
        self.ordflag = False

    def merge(self, curr, next):
        ctext, cnum, ntext, nnum = curr + next

        if ctext.endswith("dve") and self.ordflag and nnum <= 1000000:
            ctext = ctext[:len(ctext)-1] + "a"

        if ctext == "dve" and not self.ordflag and nnum < 1000000000:
            ctext = "dva"

        if (ctext.endswith("tri") or ctext.endswith("štiri")) and\
           nnum == 1000000 and not self.ordflag:
            if ctext.endswith("štiri"):
                ctext = ctext[:-1]
            ctext = ctext + "je"

        if cnum >= 20 and cnum < 100 and nnum == 2:
            ntext = "dva"

        if ctext.endswith("ena") and nnum >= 1000:
            ctext = ctext[0:-1]

        if cnum == 1:
            if nnum < 10**6 or self.ordflag:
                return next
            ctext = ""

        if nnum > cnum:
            if nnum >= 10**6:
                if self.ordflag:
                    ntext += "t"

                elif cnum == 2:
                    if ntext.endswith("d"):
                        ntext += "i"
                    else:
                        ntext += "a"

                elif 2 < cnum < 5:
                    if ntext.endswith("d"):
                        ntext += "e"
                    elif not ntext.endswith("d"):
                        ntext += "i"

                elif ctext.endswith("en"):
                    if ntext.endswith("d") or ntext.endswith("n"):
                        ntext += ""

                elif ctext.endswith("dve") and ntext.endswith("n"):
                    ctext = ctext[:-1] + "a"
                    ntext += "a"

                elif ctext.endswith("je") and ntext.endswith("n"):
                    ntext += "i"

                else:
                    if ntext.endswith("d"):
                        ntext += "a"
                    elif ntext.endswith("n"):
                        ntext += ""
                    elif ntext.endswith("d"):
                        ntext += "e"
                    else:
                        ntext += "ov"

            if nnum >= 10**2 and self.ordflag is False and ctext:
                ctext += " "

            val = cnum * nnum
        else:
            if nnum < 10 < cnum < 100:
                ntext, ctext = ctext, ntext + "in"
            elif cnum >= 10**2 and self.ordflag is False:
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
        return outword + "i"

    # Is this correct??
    def to_ordinal_num(self, value):
        self.verify_ordinal(value)
        return str(value) + "."

    def to_currency(self, val, longval=True, old=False):
        if old:
            return self.to_splitnum(val, hightxt="evro/a/v",
                                    lowtxt="stotin/a/i/ov",
                                    jointxt="in", longval=longval)
        return super(Num2Word_SL, self).to_currency(val, jointxt="in",
                                                    longval=longval)

    def to_year(self, val, longval=True):
        if not (val//100) % 10:
            return self.to_cardinal(val)
        return self.to_splitnum(val, hightxt="hundert", longval=longval)
