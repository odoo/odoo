# -*- coding: utf-8 -*-
# Copyright (c) 2018-2019, Filippo Costa.  All Rights Reserved.

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

# Globals
# -------

ZERO = "zero"

CARDINAL_WORDS = [
    ZERO, "uno", "due", "tre", "quattro", "cinque", "sei", "sette", "otto",
    "nove", "dieci", "undici", "dodici", "tredici", "quattordici", "quindici",
    "sedici", "diciassette", "diciotto", "diciannove"
]

ORDINAL_WORDS = [
    ZERO, "primo", "secondo", "terzo", "quarto", "quinto", "sesto", "settimo",
    "ottavo", "nono", "decimo", "undicesimo", "dodicesimo", "tredicesimo",
    "quattordicesimo", "quindicesimo", "sedicesimo", "diciassettesimo",
    "diciottesimo", "diciannovesimo"
]

# The script can extrapolate the missing numbers from the base forms.
STR_TENS = {2: "venti", 3: "trenta", 4: "quaranta", 6: "sessanta"}

# These prefixes are used for extremely big numbers.
EXPONENT_PREFIXES = [
    ZERO, "m", "b", "tr", "quadr", "quint", "sest", "sett", "ott", "nov", "dec"
]


GENERIC_DOLLARS = ('dollaro', 'dollari')
GENERIC_CENTS = ('centesimo', 'centesimi')
CURRENCIES_UNA = ('GBP')


# Main class
# ==========

class Num2Word_IT(Num2Word_EU):
    CURRENCY_FORMS = {
        'EUR': (('euro', 'euro'), GENERIC_CENTS),
        'USD': (GENERIC_DOLLARS, GENERIC_CENTS),
        'GBP': (('sterlina', 'sterline'), ('penny', 'penny')),
        'CNY': (('yuan', 'yuan'), ('fen', 'fen')),
    }
    MINUS_PREFIX_WORD = "meno "
    FLOAT_INFIX_WORD = " virgola "

    def setup(self):
        Num2Word_EU.setup(self)

    def __init__(self):
        pass

    def float_to_words(self, float_number, ordinal=False):
        if ordinal:
            prefix = self.to_ordinal(int(float_number))
        else:
            prefix = self.to_cardinal(int(float_number))
        float_part = str(float_number).split('.')[1]
        postfix = " ".join(
            # Drops the trailing zero and comma
            [self.to_cardinal(int(c)) for c in float_part]
        )
        return prefix + Num2Word_IT.FLOAT_INFIX_WORD + postfix

    def tens_to_cardinal(self, number):
        tens = number // 10
        units = number % 10
        if tens in STR_TENS:
            prefix = STR_TENS[tens]
        else:
            prefix = CARDINAL_WORDS[tens][:-1] + "anta"
        postfix = omitt_if_zero(CARDINAL_WORDS[units])
        return phonetic_contraction(prefix + postfix)

    def hundreds_to_cardinal(self, number):
        hundreds = number // 100
        prefix = "cento"
        if hundreds != 1:
            prefix = CARDINAL_WORDS[hundreds] + prefix
        postfix = omitt_if_zero(self.to_cardinal(number % 100))
        return phonetic_contraction(prefix + postfix)

    def thousands_to_cardinal(self, number):
        thousands = number // 1000
        if thousands == 1:
            prefix = "mille"
        else:
            prefix = self.to_cardinal(thousands) + "mila"
        postfix = omitt_if_zero(self.to_cardinal(number % 1000))
        # "mille" and "mila" don't need any phonetic contractions
        return prefix + postfix

    def big_number_to_cardinal(self, number):
        digits = [c for c in str(number)]
        length = len(digits)
        if length >= 66:
            raise NotImplementedError("The given number is too large.")
        # This is how many digits come before the "illion" term.
        #   cento miliardi => 3
        #   dieci milioni => 2
        #   un miliardo => 1
        predigits = length % 3 or 3
        multiplier = digits[:predigits]
        exponent = digits[predigits:]
        # Default infix string: "milione", "biliardo", "sestilione", ecc.
        infix = exponent_length_to_string(len(exponent))
        if multiplier == ["1"]:
            prefix = "un "
        else:
            prefix = self.to_cardinal(int("".join(multiplier)))
            # Plural form      ~~~~~~~~~~~
            infix = " " + infix[:-1] + "i"
        # Read as: Does the value of exponent equal 0?
        if set(exponent) != set("0"):
            postfix = self.to_cardinal(int("".join(exponent)))
            if " e " in postfix:
                infix += ", "
            else:
                infix += " e "
        else:
            postfix = ""
        return prefix + infix + postfix

    def to_cardinal(self, number):
        if number < 0:
            string = Num2Word_IT.MINUS_PREFIX_WORD + self.to_cardinal(-number)
        elif isinstance(number, float):
            string = self.float_to_words(number)
        elif number < 20:
            string = CARDINAL_WORDS[int(number)]
        elif number < 100:
            string = self.tens_to_cardinal(int(number))
        elif number < 1000:
            string = self.hundreds_to_cardinal(int(number))
        elif number < 1000000:
            string = self.thousands_to_cardinal(int(number))
        else:
            string = self.big_number_to_cardinal(number)
        return accentuate(string)

    def to_ordinal(self, number):
        tens = number % 100
        # Italian grammar is poorly defined here ¯\_(ツ)_/¯:
        #   centodecimo VS centodieciesimo VS centesimo decimo?
        is_outside_teens = not 10 < tens < 20
        if number < 0:
            return Num2Word_IT.MINUS_PREFIX_WORD + self.to_ordinal(-number)
        elif number % 1 != 0:
            return self.float_to_words(number, ordinal=True)
        elif number < 20:
            return ORDINAL_WORDS[int(number)]
        elif is_outside_teens and tens % 10 == 3:
            # Gets rid of the accent
            return self.to_cardinal(number)[:-1] + "eesimo"
        elif is_outside_teens and tens % 10 == 6:
            return self.to_cardinal(number) + "esimo"
        else:
            string = self.to_cardinal(number)[:-1]
            if string[-3:] == "mil":
                string += "l"
            return string + "esimo"

    def to_currency(self, val, currency='EUR', cents=True, separator=' e',
                    adjective=False):
        result = super(Num2Word_IT, self).to_currency(
            val, currency=currency, cents=cents, separator=separator,
            adjective=adjective)
        # Handle exception. In italian language is "un euro",
        # "un dollaro" etc. (not "uno euro", "uno dollaro").
        # There is an exception, some currencies need "una":
        # e.g. "una sterlina"
        if currency in CURRENCIES_UNA:
            list_result = result.split(" ")
            if list_result[0] == "uno":
                list_result[0] = list_result[0].replace("uno", "una")
                result = " ".join(list_result)
        result = result.replace("uno", "un")
        return result

# Utils
# =====


def phonetic_contraction(string):
    return (string
            .replace("oo", "o")  # ex. "centootto"
            .replace("ao", "o")  # ex. "settantaotto"
            .replace("io", "o")  # ex. "ventiotto"
            .replace("au", "u")  # ex. "trentauno"
            .replace("iu", "u")  # ex. "ventiunesimo"
            )


def exponent_length_to_string(exponent_length):
    # We always assume `exponent` to be a multiple of 3. If it's not true, then
    # Num2Word_IT.big_number_to_cardinal did something wrong.
    prefix = EXPONENT_PREFIXES[exponent_length // 6]
    if exponent_length % 6 == 0:
        return prefix + "ilione"
    else:
        return prefix + "iliardo"


def accentuate(string):
    # This is inefficient: it may do several rewritings when deleting
    # half-sentence accents. However, it is the easiest method and speed is
    # not crucial (duh), so...
    return " ".join(
        # Deletes half-sentence accents and accentuates the last "tre"
        [w.replace("tré", "tre")[:-3] + "tré"
         # We shouldn't accentuate a single "tre": is has to be a composite
         # word.                ~~~~~~~~~~
         if w[-3:] == "tre" and len(w) > 3
         # Deletes half-sentence accents anyway
         #     ~~~~~~~~~~~~~~~~~~~~~~
         else w.replace("tré", "tre")
         for w in string.split()
         ])


def omitt_if_zero(number_to_string):
    return "" if number_to_string == ZERO else number_to_string
