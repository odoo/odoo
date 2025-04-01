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

from __future__ import print_function, unicode_literals

from .lang_EU import Num2Word_EU


class Num2Word_FR(Num2Word_EU):
    def setup(self):
        Num2Word_EU.setup(self)

        self.negword = "moins "
        self.pointword = "virgule"
        self.errmsg_nonnum = (
            u"Seulement des nombres peuvent être convertis en mots."
            )
        self.errmsg_toobig = u"Nombre trop grand pour être converti en mots."
        self.exclude_title = ["et", "virgule", "moins"]
        self.mid_numwords = [(1000, "mille"), (100, "cent"),
                             (80, "quatre-vingts"), (60, "soixante"),
                             (50, "cinquante"), (40, "quarante"),
                             (30, "trente")]
        self.low_numwords = ["vingt", "dix-neuf", "dix-huit", "dix-sept",
                             "seize", "quinze", "quatorze", "treize", "douze",
                             "onze", "dix", "neuf", "huit", "sept", "six",
                             "cinq", "quatre", "trois", "deux", "un", "zéro"]
        self.ords = {
            "cinq": "cinquième",
            "neuf": "neuvième",
        }

    def merge(self, curr, next):
        ctext, cnum, ntext, nnum = curr + next

        if cnum == 1:
            if nnum < 1000000:
                return next
        else:
            if (not (cnum - 80) % 100
                or (not cnum % 100 and cnum < 1000))\
                    and nnum < 1000000 \
                    and ctext[-1] == "s":
                ctext = ctext[:-1]
            if cnum < 1000 and nnum != 1000 and \
                    ntext[-1] != "s" and not nnum % 100:
                ntext += "s"

        if nnum < cnum < 100:
            if nnum % 10 == 1 and cnum != 80:
                return ("%s et %s" % (ctext, ntext), cnum + nnum)
            return ("%s-%s" % (ctext, ntext), cnum + nnum)
        if nnum > cnum:
            return ("%s %s" % (ctext, ntext), cnum * nnum)
        return ("%s %s" % (ctext, ntext), cnum + nnum)

    # Is this right for such things as 1001 - "mille unième" instead of
    # "mille premier"??  "millième"??

    def to_ordinal(self, value):
        self.verify_ordinal(value)
        if value == 1:
            return "premier"
        word = self.to_cardinal(value)
        for src, repl in self.ords.items():
            if word.endswith(src):
                word = word[:-len(src)] + repl
                break
        else:
            if word[-1] == "e":
                word = word[:-1]
            word = word + "ième"
        return word

    def to_ordinal_num(self, value):
        self.verify_ordinal(value)
        out = str(value)
        out += {"1": "er"}.get(out[-1], "me")
        return out

    def to_currency(self, val, longval=True, old=False):
        hightxt = "euro/s"
        if old:
            hightxt = "franc/s"
        cents = int(round(val*100))
        return self.to_splitnum(cents, hightxt=hightxt, lowtxt="centime/s",
                                divisor=100, jointxt="et", longval=longval)
