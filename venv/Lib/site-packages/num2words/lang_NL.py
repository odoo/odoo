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


class Num2Word_NL(Num2Word_EU):
    CURRENCY_FORMS = {
        'EUR': (('euro', 'euros'), ('cent', 'cents')),
    }

    GIGA_SUFFIX = "iljard"
    MEGA_SUFFIX = "iljoen"

    def setup(self):
        super(Num2Word_NL, self).setup()

        self.negword = "min "
        self.pointword = "komma"
        # "Cannot treat float %s as ordinal."
        self.errmsg_floatord = (
            "Het zwevende puntnummer %s kan niet omgezet worden " +
            "naar een ordernummer."
        )
        # "type(((type(%s)) ) not in [long, int, float]"
        self.errmsg_nonnum = (
            "Alleen nummers (type (%s)) kunnen naar " +
            "woorden omgezet worden."
        )
        # "Cannot treat negative num %s as ordinal."
        self.errmsg_negord = (
            "Het negatieve getal %s kan niet omgezet " +
            "worden naar een ordernummer."
        )
        # "abs(%s) must be less than %s."
        self.errmsg_toobig = "Het getal %s moet minder zijn dan %s."
        self.exclude_title = []

        lows = ["non", "okt", "sept", "sext", "quint", "quadr", "tr", "b", "m"]
        units = ["", "un", "duo", "tre", "quattuor", "quin", "sex", "sept",
                 "okto", "novem"]
        tens = ["dez", "vigint", "trigint", "quadragint", "quinquagint",
                "sexagint", "septuagint", "oktogint", "nonagint"]

        self.high_numwords = (
            ["zend"] + self.gen_high_numwords(units, tens, lows))

        self.mid_numwords = [(1000, "duizend"), (100, "honderd"),
                             (90, "negentig"), (80, "tachtig"),
                             (70, "zeventig"), (60, "zestig"),
                             (50, "vijftig"), (40, "veertig"),
                             (30, "dertig")]

        self.low_numwords = ["twintig", "negentien", "achttien", "zeventien",
                             "zestien", "vijftien", "veertien", "dertien",
                             "twaalf", "elf", "tien", "negen", "acht", "zeven",
                             "zes", "vijf", "vier", "drie", "twee", "één",
                             "nul"]

        self.ords = {"één": "eerst",
                     "twee": "tweed",
                     "drie": "derd",
                     "vier": "vierd",
                     "vijf": "vijfd",
                     "zes": "zesd",
                     "zeven": "zevend",
                     "acht": "achtst",
                     "negen": "negend",
                     "tien": "tiend",
                     "elf": "elfd",
                     "twaalf": "twaalfd",

                     "ig": "igst",
                     "erd": "erdst",
                     "end": "endst",
                     "joen": "joenst",
                     "rd": "rdst"}

    def merge(self, curr, next):
        ctext, cnum, ntext, nnum = curr + next

        if cnum == 1:
            if nnum < 10 ** 6:
                return next
            ctext = "een"

        if nnum > cnum:
            if nnum >= 10 ** 6:
                ctext += " "
            val = cnum * nnum
        else:
            if nnum < 10 < cnum < 100:
                if nnum == 1:
                    ntext = "een"

                if ntext.endswith("e"):
                    ntext += "ën"  # "n"
                else:
                    ntext += "en"
                ntext, ctext = ctext, ntext  # + "en"
            elif cnum >= 10 ** 6:
                ctext += " "
            val = cnum + nnum

        word = ctext + ntext
        return word, val

    def to_ordinal(self, value):
        self.verify_ordinal(value)
        outword = self.to_cardinal(value)
        for key in self.ords:
            if outword.endswith(key):
                outword = outword[:len(outword) - len(key)] + self.ords[key]
                break
        return outword + "e"

    def to_ordinal_num(self, value):
        self.verify_ordinal(value)
        return str(value) + "."

    def pluralize(self, n, forms):
        """
        :param n:
        :param forms:
        :return:

        gettext form is nplurals=2; plural=(n != 1);
        but this claims https://onzetaal.nl/taaladvies/euro-euros/
        not sure if it's applied only to euro
        """
        return forms[0]

    def to_year(self, val, longval=True):
        if not (val // 100) % 10:
            return self.to_cardinal(val)
        return self.to_splitnum(val, hightxt="honderd", longval=longval)
