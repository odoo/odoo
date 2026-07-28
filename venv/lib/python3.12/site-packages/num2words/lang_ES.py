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

import math

from .lang_EU import Num2Word_EU

GENERIC_DOLLARS = ('dólar', 'dólares')
GENERIC_CENTS = ('centavo', 'centavos')
CURRENCIES_UNA = ('SLL', 'SEK', 'NOK', 'CZK', 'DKK', 'ISK',
                  'SKK', 'GBP', 'CYP', 'EGP', 'FKP', 'GIP',
                  'LBP', 'SDG', 'SHP', 'SSP', 'SYP', 'INR',
                  'IDR', 'LKR', 'MUR', 'NPR', 'PKR', 'SCR',
                  'ESP', 'TRY', 'ITL')
CENTS_UNA = ('EGP', 'JOD', 'LBP', 'SDG', 'SSP', 'SYP')


class Num2Word_ES(Num2Word_EU):
    CURRENCY_FORMS = {
        'EUR': (('euro', 'euros'), ('céntimo', 'céntimos')),
        'ESP': (('peseta', 'pesetas'), ('céntimo', 'céntimos')),
        'USD': (GENERIC_DOLLARS, GENERIC_CENTS),
        'PEN': (('sol', 'soles'), ('céntimo', 'céntimos')),
        'CRC': (('colón', 'colones'), GENERIC_CENTS),
        'AUD': (GENERIC_DOLLARS, GENERIC_CENTS),
        'CAD': (GENERIC_DOLLARS, GENERIC_CENTS),
        'GBP': (('libra', 'libras'), ('penique', 'peniques')),
        'RUB': (('rublo', 'rublos'), ('kopeyka', 'kopeykas')),
        'SEK': (('corona', 'coronas'), ('öre', 'öre')),
        'NOK': (('corona', 'coronas'), ('øre', 'øre')),
        'PLN': (('zloty', 'zlotys'), ('grosz', 'groszy')),
        'MXN': (('peso', 'pesos'), GENERIC_CENTS),
        'RON': (('leu', 'leus'), ('ban', 'bani')),
        'INR': (('rupia', 'rupias'), ('paisa', 'paisas')),
        'HUF': (('florín', 'florines'), ('fillér', 'fillér')),
        'FRF': (('franco', 'francos'), ('céntimo', 'céntimos')),
        'CNY': (('yuan', 'yuanes'), ('fen', 'jiaos')),
        'CZK': (('corona', 'coronas'), ('haléř', 'haléř')),
        'NIO': (('córdoba', 'córdobas'), GENERIC_CENTS),
        'VES': (('bolívar', 'bolívares'), ('céntimo', 'céntimos')),
        'BRL': (('real', 'reales'), GENERIC_CENTS),
        'CHF': (('franco', 'francos'), ('céntimo', 'céntimos')),
        'JPY': (('yen', 'yenes'), ('sen', 'sen')),
        'KRW': (('won', 'wones'), ('jeon', 'jeon')),
        'KPW': (('won', 'wones'), ('chon', 'chon')),
        'TRY': (('lira', 'liras'), ('kuruş', 'kuruş')),
        'ZAR': (('rand', 'rands'), ('céntimo', 'céntimos')),
        'KZT': (('tenge', 'tenges'), ('tïın', 'tïın')),
        'UAH': (('hryvnia', 'hryvnias'), ('kopiyka', 'kopiykas')),
        'THB': (('baht', 'bahts'), ('satang', 'satang')),
        'AED': (('dirham', 'dirhams'), ('fils', 'fils')),
        'AFN': (('afghani', 'afghanis'), ('pul', 'puls')),
        'ALL': (('lek ', 'leke'), ('qindarkë', 'qindarka')),
        'AMD': (('dram', 'drams'), ('luma', 'lumas')),
        'ANG': (('florín', 'florines'), GENERIC_CENTS),
        'AOA': (('kwanza', 'kwanzas'), ('céntimo', 'céntimos')),
        'ARS': (('peso', 'pesos'), GENERIC_CENTS),
        'AWG': (('florín', 'florines'), GENERIC_CENTS),
        'AZN': (('manat', 'manat'), ('qəpik', 'qəpik')),
        'BBD': (GENERIC_DOLLARS, GENERIC_CENTS),
        'BDT': (('taka', 'takas'), ('paisa', 'paisas')),
        'BGN': (('lev', 'leva'), ('stotinka', 'stotinki')),
        'BHD': (('dinar', 'dinares'), ('fils', 'fils')),
        'BIF': (('franco', 'francos'), ('céntimo', 'céntimos')),
        'BMD': (GENERIC_DOLLARS, GENERIC_CENTS),
        'BND': (GENERIC_DOLLARS, GENERIC_CENTS),
        'BOB': (('boliviano', 'bolivianos'), GENERIC_CENTS),
        'BSD': (GENERIC_DOLLARS, GENERIC_CENTS),
        'BTN': (('ngultrum', 'ngultrum'), ('chetrum', 'chetrum')),
        'BWP': (('pula', 'pulas'), ('thebe', 'thebes')),
        'BYN': (('rublo', 'rublos'), ('kópek', 'kópeks')),
        'BYR': (('rublo', 'rublos'), ('kópek', 'kópeks')),
        'BZD': (GENERIC_DOLLARS, ('céntimo', 'céntimos')),
        'CDF': (('franco', 'francos'), ('céntimo', 'céntimos')),
        'CLP': (('peso', 'pesos'), GENERIC_CENTS),
        'COP': (('peso', 'pesos'), GENERIC_CENTS),
        'CUP': (('peso', 'pesos'), GENERIC_CENTS),
        'CVE': (('escudo', 'escudos'), GENERIC_CENTS),
        'CYP': (('libra', 'libras'), ('céntimo', 'céntimos')),
        'DJF': (('franco', 'francos'), ('céntimo', 'céntimos')),
        'DKK': (('corona', 'coronas'), ('øre', 'øre')),
        'DOP': (('peso', 'pesos'), GENERIC_CENTS),
        'DZD': (('dinar', 'dinares'), ('céntimo', 'céntimos')),
        'ECS': (('sucre', 'sucres'), GENERIC_CENTS),
        'EGP': (('libra', 'libras'), ('piastra', 'piastras')),
        'ERN': (('nakfa', 'nakfas'), ('céntimo', 'céntimos')),
        'ETB': (('birr', 'birrs'), ('céntimo', 'céntimos')),
        'FJD': (GENERIC_DOLLARS, GENERIC_CENTS),
        'FKP': (('libra', 'libras'), ('penique', 'peniques')),
        'GEL': (('lari', 'laris'), ('tetri', 'tetris')),
        'GHS': (('cedi', 'cedis'), ('pesewa', 'pesewas')),
        'GIP': (('libra', 'libras'), ('penique', 'peniques')),
        'GMD': (('dalasi', 'dalasis'), ('butut', 'bututs')),
        'GNF': (('franco', 'francos'), ('céntimo', 'céntimos')),
        'GTQ': (('quetzal', 'quetzales'), GENERIC_CENTS),
        'GYD': (GENERIC_DOLLARS, GENERIC_CENTS),
        'HKD': (GENERIC_DOLLARS, GENERIC_CENTS),
        'HNL': (('lempira', 'lempiras'), GENERIC_CENTS),
        'HRK': (('kuna', 'kunas'), ('lipa', 'lipas')),
        'HTG': (('gourde', 'gourdes'), ('céntimo', 'céntimos')),
        'IDR': (('rupia', 'rupias'), ('céntimo', 'céntimos')),
        'ILS': (('séquel', 'séqueles'), ('agora', 'agoras')),
        'IQD': (('dinar', 'dinares'), ('fils', 'fils')),
        'IRR': (('rial', 'riales'), ('dinar', 'dinares')),
        'ISK': (('corona', 'coronas'), ('eyrir', 'aurar')),
        'ITL': (('lira', 'liras'), ('céntimo', 'céntimos')),
        'JMD': (GENERIC_DOLLARS, ('céntimo', 'céntimos')),
        'JOD': (('dinar', 'dinares'), ('piastra', 'piastras')),
        'KES': (('chelín', 'chelines'), ('céntimo', 'céntimos')),
        'KGS': (('som', 'som'), ('tyiyn', 'tyiyn')),
        'KHR': (('riel', 'rieles'), ('céntimo', 'céntimos')),
        'KMF': (('franco', 'francos'), ('céntimo', 'céntimos')),
        'KWD': (('dinar', 'dinares'), ('fils', 'fils')),
        'KYD': (GENERIC_DOLLARS, ('céntimo', 'céntimos')),
        'LAK': (('kip', 'kips'), ('att', 'att')),
        'LBP': (('libra', 'libras'), ('piastra', 'piastras')),
        'LKR': (('rupia', 'rupias'), ('céntimo', 'céntimos')),
        'LRD': (GENERIC_DOLLARS, ('céntimo', 'céntimos')),
        'LSL': (('loti', 'lotis'), ('céntimo', 'céntimos')),
        'LTL': (('lita', 'litas'), ('céntimo', 'céntimos')),
        'LVL': (('lat', 'lats'), ('céntimo', 'céntimos')),
        'LYD': (('dinar', 'dinares'), ('dírham', 'dírhams')),
        'MAD': (('dírham', 'dirhams'), ('céntimo', 'céntimos')),
        'MDL': (('leu', 'lei'), ('ban', 'bani')),
        'MGA': (('ariary', 'ariaris'), ('iraimbilanja', 'iraimbilanja')),
        'MKD': (('denar', 'denares'), ('deni', 'denis')),
        'MMK': (('kiat', 'kiats'), ('pya', 'pyas')),
        'MNT': (('tugrik', 'tugriks'), ('möngö', 'möngö')),
        'MOP': (('pataca', 'patacas'), ('avo', 'avos')),
        'MRO': (('ouguiya', 'ouguiyas'), ('khoums', 'khoums')),
        'MRU': (('ouguiya', 'ouguiyas'), ('khoums', 'khoums')),
        'MUR': (('rupia', 'rupias'), ('céntimo', 'céntimos')),
        'MVR': (('rufiyaa', 'rufiyaas'), ('laari', 'laari')),
        'MWK': (('kuacha', 'kuachas'), ('tambala', 'tambalas')),
        'MYR': (('ringgit', 'ringgit'), ('céntimo', 'céntimos')),
        'MZN': (('metical', 'metical'), GENERIC_CENTS),
        'NAD': (GENERIC_DOLLARS, ('céntimo', 'céntimos')),
        'NGN': (('naira', 'nairas'), ('kobo', 'kobo')),
        'NPR': (('rupia', 'rupias'), ('paisa', 'paisas')),
        'NZD': (GENERIC_DOLLARS, GENERIC_CENTS),
        'OMR': (('rial', 'riales'), ('baisa', 'baisa')),
        'PAB': (('balboa', 'balboas'), ('centésimo', 'centésimos')),
        'PGK': (('kina', 'kinas'), ('toea', 'toea')),
        'PHP': (('peso', 'pesos'), GENERIC_CENTS),
        'PKR': (('rupia', 'rupias'), ('paisa', 'paisas')),
        'PLZ': (('zloty', 'zlotys'), ('grosz', 'groszy')),
        'PYG': (('guaraní', 'guaranís'), ('céntimo', 'céntimos')),
        'QAR': (('rial', 'riales'), ('dírham', 'dírhams')),
        'QTQ': (('quetzal', 'quetzales'), GENERIC_CENTS),
        'RSD': (('dinar', 'dinares'), ('para', 'para')),
        'RUR': (('rublo', 'rublos'), ('kopek', 'kopeks')),
        'RWF': (('franco', 'francos'), ('céntimo', 'céntimos')),
        'SAR': (('riyal', 'riales'), ('halala', 'halalas')),
        'SBD': (GENERIC_DOLLARS, ('céntimo', 'céntimos')),
        'SCR': (('rupia', 'rupias'), ('céntimo', 'céntimos')),
        'SDG': (('libra', 'libras'), ('piastra', 'piastras')),
        'SGD': (GENERIC_DOLLARS, ('céntimo', 'céntimos')),
        'SHP': (('libra', 'libras'), ('penique', 'peniques')),
        'SKK': (('corona', 'coronas'), ('halier', 'haliers')),
        'SLL': (('leona', 'leonas'), ('céntimo', 'céntimos')),
        'SRD': (GENERIC_DOLLARS, ('céntimo', 'céntimos')),
        'SSP': (('libra', 'libras'), ('piastra', 'piastras')),
        'STD': (('dobra', 'dobras'), ('céntimo', 'céntimos')),
        'SVC': (('colón', 'colones'), GENERIC_CENTS),
        'SYP': (('libra', 'libras'), ('piastra', 'piastras')),
        'SZL': (('lilangeni', 'emalangeni'), ('céntimo', 'céntimos')),
        'TJS': (('somoni', 'somonis'), ('dirame', 'dirames')),
        'TMT': (('manat', 'manat'), ('tenge', 'tenge')),
        'TND': (('dinar', 'dinares'), ('milésimo', 'milésimos')),
        'TOP': (('paanga', 'paangas'), ('céntimo', 'céntimos')),
        'TTD': (GENERIC_DOLLARS, ('céntimo', 'céntimos')),
        'TWD': (('nuevo dólar', 'nuevos dólares'), ('céntimo', 'céntimos')),
        'TZS': (('chelín', 'chelines'), ('céntimo', 'céntimos')),
        'UAG': (('hryvnia', 'hryvnias'), ('kopiyka', 'kopiykas')),
        'UGX': (('chelín', 'chelines'), ('céntimo', 'céntimos')),
        'UYU': (('peso', 'pesos'), ('centésimo', 'centésimos')),
        'UZS': (('sum', 'sum'), ('tiyin', 'tiyin')),
        'VEF': (('bolívar fuerte', 'bolívares fuertes'),
                ('céntimo', 'céntimos')),
        'VND': (('dong', 'dongs'), ('xu', 'xu')),
        'VUV': (('vatu', 'vatu'), ('nenhum', 'nenhum')),
        'WST': (('tala', 'tala'), GENERIC_CENTS),
        'XAF': (('franco CFA', 'francos CFA'), ('céntimo', 'céntimos')),
        'XCD': (GENERIC_DOLLARS, ('céntimo', 'céntimos')),
        'XOF': (('franco CFA', 'francos CFA'), ('céntimo', 'céntimos')),
        'XPF': (('franco CFP', 'francos CFP'), ('céntimo', 'céntimos')),
        'YER': (('rial', 'riales'), ('fils', 'fils')),
        'YUM': (('dinar', 'dinares'), ('para', 'para')),
        'ZMW': (('kwacha', 'kwachas'), ('ngwee', 'ngwee')),
        'ZRZ': (('zaire', 'zaires'), ('likuta', 'makuta')),
        'ZWL': (GENERIC_DOLLARS, ('céntimo', 'céntimos')),
        'ZWL': (GENERIC_DOLLARS, ('céntimo', 'céntimos')),
    }

    # //CHECK: Is this sufficient??
    GIGA_SUFFIX = None
    MEGA_SUFFIX = "illón"

    def setup(self):
        lows = ["cuatr", "tr", "b", "m"]
        self.high_numwords = self.gen_high_numwords([], [], lows)
        self.negword = "menos "
        self.pointword = "punto"
        self.errmsg_nonnum = "type(%s) no es [long, int, float]"
        self.errmsg_floatord = "El float %s no puede ser tratado como un" \
            " ordinal."
        self.errmsg_negord = "El número negativo %s no puede ser tratado" \
            " como un ordinal."
        self.errmsg_toobig = (
            "abs(%s) deber ser inferior a %s."
            )
        self.gender_stem = "o"
        self.exclude_title = ["y", "menos", "punto"]
        self.mid_numwords = [(1000, "mil"), (100, "cien"), (90, "noventa"),
                             (80, "ochenta"), (70, "setenta"), (60, "sesenta"),
                             (50, "cincuenta"), (40, "cuarenta"),
                             (30, "treinta")]
        self.low_numwords = ["veintinueve", "veintiocho", "veintisiete",
                             "veintiséis", "veinticinco", "veinticuatro",
                             "veintitrés", "veintidós", "veintiuno",
                             "veinte", "diecinueve", "dieciocho", "diecisiete",
                             "dieciséis", "quince", "catorce", "trece", "doce",
                             "once", "diez", "nueve", "ocho", "siete", "seis",
                             "cinco", "cuatro", "tres", "dos", "uno", "cero"]
        self.ords = {1: "primer",
                     2: "segund",
                     3: "tercer",
                     4: "cuart",
                     5: "quint",
                     6: "sext",
                     7: "séptim",
                     8: "octav",
                     9: "noven",
                     10: "décim",
                     20: "vigésim",
                     30: "trigésim",
                     40: "quadragésim",
                     50: "quincuagésim",
                     60: "sexagésim",
                     70: "septuagésim",
                     80: "octogésim",
                     90: "nonagésim",
                     100: "centésim",
                     200: "ducentésim",
                     300: "tricentésim",
                     400: "cuadrigentésim",
                     500: "quingentésim",
                     600: "sexcentésim",
                     700: "septigentésim",
                     800: "octigentésim",
                     900: "noningentésim",
                     1e3: "milésim",
                     1e6: "millonésim",
                     1e9: "billonésim",
                     1e12: "trillonésim",
                     1e15: "cuadrillonésim"}

    def merge(self, curr, next):
        ctext, cnum, ntext, nnum = curr + next

        if cnum == 1:
            if nnum < 1000000:
                return next
            ctext = "un"
        elif cnum == 100 and not nnum % 1000 == 0:
            ctext += "t" + self.gender_stem

        if nnum < cnum:
            if cnum < 100:
                return "%s y %s" % (ctext, ntext), cnum + nnum
            return "%s %s" % (ctext, ntext), cnum + nnum
        elif (not nnum % 1000000) and cnum > 1:
            ntext = ntext[:-3] + "lones"

        if nnum == 100:
            if cnum == 5:
                ctext = "quinien"
                ntext = ""
            elif cnum == 7:
                ctext = "sete"
            elif cnum == 9:
                ctext = "nove"
            ntext += "t" + self.gender_stem + "s"
        else:
            ntext = " " + ntext

        return (ctext + ntext, cnum * nnum)

    def to_ordinal(self, value):
        self.verify_ordinal(value)
        if value == 0:
            text = ""
        elif value <= 10:
            text = "%s%s" % (self.ords[value], self.gender_stem)
        elif value <= 12:
            text = (
                "%s%s%s" % (self.ords[10], self.gender_stem,
                            self.to_ordinal(value - 10))
                    )
        elif value <= 100:
            dec = (value // 10) * 10
            text = (
                "%s%s %s" % (self.ords[dec], self.gender_stem,
                             self.to_ordinal(value - dec))
                    )
        elif value <= 1e3:
            cen = (value // 100) * 100
            text = (
                "%s%s %s" % (self.ords[cen], self.gender_stem,
                             self.to_ordinal(value - cen))
                    )
        elif value < 1e18:
            # Round down to the nearest 1e(3n)
            # dec contains the following:
            # [ 1e3,  1e6): 1e3
            # [ 1e6,  1e9): 1e6
            # [ 1e9, 1e12): 1e9
            # [1e12, 1e15): 1e12
            # [1e15, 1e18): 1e15
            dec = 1000 ** int(math.log(int(value), 1000))

            # Split the parts before and after the word for 'dec'
            # eg (12, 345) = divmod(12_345, 1_000)
            high_part, low_part = divmod(value, dec)

            cardinal = self.to_cardinal(high_part) if high_part != 1 else ""
            text = (
                "%s%s%s %s" % (cardinal, self.ords[dec], self.gender_stem,
                               self.to_ordinal(low_part))
                    )
        else:
            text = self.to_cardinal(value)
        return text.strip()

    def to_ordinal_num(self, value):
        self.verify_ordinal(value)
        return "%s%s" % (value, "º" if self.gender_stem == 'o' else "ª")

    def to_currency(self, val, currency='EUR', cents=True, separator=' con',
                    adjective=False):
        result = super(Num2Word_ES, self).to_currency(
            val, currency=currency, cents=cents, separator=separator,
            adjective=adjective)
        # Handle exception: In Spanish it's "un euro" and not "uno euro",
        # except in these currencies, where it's "una": leona, corona,
        # libra, lira, rupia, lempira, peseta.
        # The same goes for "veintiuna", "treinta y una"...
        # Also, this needs to be handled separately for "dollars" and
        # "cents".
        # All "cents" are masculine except for: piastra.
        # Source: https://www.rae.es/dpd/una (section 2.2)

        # split "dollars" part from "cents" part
        list_result = result.split(separator + " ")

        # "DOLLARS" PART (list_result[0])

        # Feminine currencies ("una libra", "trescientas libras"...)
        if currency in CURRENCIES_UNA:

            # "una libra", "veintiuna libras", "treinta y una libras"...
            list_result[0] = list_result[0].replace("uno", "una")

            # "doscientas libras", "trescientas libras"...
            list_result[0] = list_result[0].replace("cientos", "cientas")

        # Masc.: Correct orthography for the specific case of "veintiún":
        list_result[0] = list_result[0].replace("veintiuno", "veintiún")

        # Masculine currencies: general case ("un euro", "treinta y un
        # euros"...):
        list_result[0] = list_result[0].replace("uno", "un")

        # "CENTS" PART (list_result[1])

        # Feminine "cents" ("una piastra", "veintiuna piastras"...)
        if currency in CENTS_UNA:

            # "una piastra", "veintiuna piastras", "treinta y una piastras"...
            list_result[1] = list_result[1].replace("uno", "una")

        # Masc.: Correct orthography for the specific case of "veintiún":
        list_result[1] = list_result[1].replace("veintiuno", "veintiún")

        # Masculine "cents": general case ("un centavo", "treinta y un
        # centavos"...):
        list_result[1] = list_result[1].replace("uno", "un")

        # join back "dollars" part with "cents" part
        result = (separator + " ").join(list_result)

        return result
