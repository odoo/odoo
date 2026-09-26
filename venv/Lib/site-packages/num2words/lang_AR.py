# -*- coding: utf-8 -*-
# Copyright (c) 2003, Taro Ogawa.  All Rights Reserved.
# Copyright (c) 2013, Savoir-faire Linux inc.  All Rights Reserved.
# Copyright (c) 2018, Abdullah Alhazmy, Alhazmy13.  All Rights Reserved.


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

import re
from decimal import Decimal
from math import floor

CURRENCY_SR = [("ريال", "ريالان", "ريالات", "ريالاً"),
               ("هللة", "هللتان", "هللات", "هللة")]
CURRENCY_EGP = [("جنيه", "جنيهان", "جنيهات", "جنيهاً"),
                ("قرش", "قرشان", "قروش", "قرش")]
CURRENCY_KWD = [("دينار", "ديناران", "دينارات", "ديناراً"),
                ("فلس", "فلسان", "فلس", "فلس")]

ARABIC_ONES = [
    "", "واحد", "اثنان", "ثلاثة", "أربعة", "خمسة", "ستة", "سبعة", "ثمانية",
    "تسعة",
    "عشرة", "أحد عشر", "اثنا عشر", "ثلاثة عشر", "أربعة عشر", "خمسة عشر",
    "ستة عشر", "سبعة عشر", "ثمانية عشر",
    "تسعة عشر"
]


class Num2Word_AR(object):
    errmsg_too_big = "Too large"
    max_num = 10 ** 36

    def __init__(self):
        self.number = 0
        self.arabicPrefixText = ""
        self.arabicSuffixText = ""
        self.integer_value = 0
        self._decimalValue = ""
        self.partPrecision = 2
        self.currency_unit = CURRENCY_SR[0]
        self.currency_subunit = CURRENCY_SR[1]
        self.isCurrencyPartNameFeminine = True
        self.isCurrencyNameFeminine = False
        self.separator = 'و'

        self.arabicOnes = ARABIC_ONES
        self.arabicFeminineOnes = [
            "", "إحدى", "اثنتان", "ثلاث", "أربع", "خمس", "ست", "سبع", "ثمان",
            "تسع",
            "عشر", "إحدى عشرة", "اثنتا عشرة", "ثلاث عشرة", "أربع عشرة",
            "خمس عشرة", "ست عشرة", "سبع عشرة", "ثماني عشرة",
            "تسع عشرة"
        ]
        self.arabicOrdinal = [
            "", "اول", "ثاني", "ثالث", "رابع", "خامس", "سادس", "سابع", "ثامن",
            "تاسع", "عاشر", "حادي عشر", "ثاني عشر", "ثالث عشر", "رابع عشر",
            "خامس عشر", "سادس عشر", "سابع عشر", "ثامن عشر", "تاسع عشر"
        ]
        self.arabicTens = [
            "عشرون", "ثلاثون", "أربعون", "خمسون", "ستون", "سبعون", "ثمانون",
            "تسعون"
        ]
        self.arabicHundreds = [
            "", "مائة", "مئتان", "ثلاثمائة", "أربعمائة", "خمسمائة", "ستمائة",
            "سبعمائة", "ثمانمائة", "تسعمائة"
        ]
        self.arabicAppendedTwos = [
            "مئتا", "ألفا", "مليونا", "مليارا", "تريليونا", "كوادريليونا",
            "كوينتليونا", "سكستيليونا"
        ]
        self.arabicTwos = [
            "مئتان", "ألفان", "مليونان", "ملياران", "تريليونان",
            "كوادريليونان", "كوينتليونان", "سكستيليونان"
        ]
        self.arabicGroup = [
            "مائة", "ألف", "مليون", "مليار", "تريليون", "كوادريليون",
            "كوينتليون", "سكستيليون"
        ]
        self.arabicAppendedGroup = [
            "", "ألفاً", "مليوناً", "ملياراً", "تريليوناً", "كوادريليوناً",
            "كوينتليوناً", "سكستيليوناً"
        ]
        self.arabicPluralGroups = [
            "", "آلاف", "ملايين", "مليارات", "تريليونات", "كوادريليونات",
            "كوينتليونات", "سكستيليونات"
        ]

    def number_to_arabic(self, arabic_prefix_text, arabic_suffix_text):
        self.arabicPrefixText = arabic_prefix_text
        self.arabicSuffixText = arabic_suffix_text
        self.extract_integer_and_decimal_parts()

    def extract_integer_and_decimal_parts(self):
        re.split('\\.', str(self.number))
        splits = re.split('\\.', str(self.number))

        self.integer_value = int(splits[0])
        if len(splits) > 1:
            self._decimalValue = int(self.decimal_value(splits[1]))
        else:
            self._decimalValue = 0

    def decimal_value(self, decimal_part):

        if self.partPrecision is not len(decimal_part):
            decimal_part_length = len(decimal_part)

            decimal_part_builder = decimal_part
            for i in range(0, self.partPrecision - decimal_part_length):
                decimal_part_builder += '0'
            decimal_part = decimal_part_builder

            if len(decimal_part) <= self.partPrecision:
                dec = len(decimal_part)
            else:
                dec = self.partPrecision
            result = decimal_part[0: dec]
        else:
            result = decimal_part

        for i in range(len(result), self.partPrecision):
            result += '0'
        return result

    def digit_feminine_status(self, digit, group_level):
        if group_level == -1:
            if self.isCurrencyPartNameFeminine:
                return self.arabicFeminineOnes[int(digit)]
            else:
                return self.arabicOnes[int(digit)]
        elif group_level == 0:
            if self.isCurrencyNameFeminine:
                return self.arabicFeminineOnes[int(digit)]
            else:
                return self.arabicOnes[int(digit)]

        else:
            return self.arabicOnes[int(digit)]

    def process_arabic_group(self, group_number, group_level,
                             remaining_number):
        tens = Decimal(group_number) % Decimal(100)
        hundreds = Decimal(group_number) / Decimal(100)
        ret_val = ""

        if int(hundreds) > 0:
            if tens == 0 and int(hundreds) == 2:
                ret_val = "{}".format(self.arabicAppendedTwos[0])
            else:
                ret_val = "{}".format(self.arabicHundreds[int(hundreds)])

        if tens > 0:
            if tens < 20:
                if tens == 2 and int(hundreds) == 0 and group_level > 0:
                    if self.integer_value in [2000, 2000000, 2000000000,
                                              2000000000000, 2000000000000000,
                                              2000000000000000000]:
                        ret_val = "{}".format(
                            self.arabicAppendedTwos[int(group_level)])
                    else:
                        ret_val = "{}".format(
                            self.arabicTwos[int(group_level)])
                else:
                    if ret_val != "":
                        ret_val += " و "

                    if tens == 1 and group_level > 0 and hundreds == 0:
                        ret_val += ""
                    elif (tens == 1 or tens == 2) and (
                            group_level == 0 or group_level == -1) and \
                            hundreds == 0 and remaining_number == 0:
                        ret_val += ""
                    else:
                        ret_val += self.digit_feminine_status(int(tens),
                                                              group_level)
            else:
                ones = tens % 10
                tens = (tens / 10) - 2
                if ones > 0:
                    if ret_val != "" and tens < 4:
                        ret_val += " و "

                    ret_val += self.digit_feminine_status(ones, group_level)
                if ret_val != "" and ones != 0:
                    ret_val += " و "

                ret_val += self.arabicTens[int(tens)]

        return ret_val

    def convert(self, value):
        self.number = "{:.9f}".format(value)
        self.number_to_arabic(self.arabicPrefixText, self.arabicSuffixText)
        return self.convert_to_arabic()

    def convert_to_arabic(self):
        temp_number = Decimal(self.number)

        if temp_number == Decimal(0):
            return "صفر"

        decimal_string = self.process_arabic_group(self._decimalValue,
                                                   -1,
                                                   Decimal(0))
        ret_val = ""
        group = 0

        while temp_number > Decimal(0):

            number_to_process = int(
                Decimal(str(temp_number)) % Decimal(str(1000)))
            temp_number = int(Decimal(temp_number) / Decimal(1000))

            group_description = \
                self.process_arabic_group(number_to_process,
                                          group,
                                          Decimal(floor(temp_number)))
            if group_description != '':
                if group > 0:
                    if ret_val != "":
                        ret_val = "{} و {}".format("", ret_val)
                    if number_to_process != 2:
                        if number_to_process % 100 != 1:
                            if 3 <= number_to_process <= 10:
                                ret_val = "{} {}".format(
                                    self.arabicPluralGroups[group], ret_val)
                            else:
                                if ret_val != "":
                                    ret_val = "{} {}".format(
                                        self.arabicAppendedGroup[group],
                                        ret_val)
                                else:
                                    ret_val = "{} {}".format(
                                        self.arabicGroup[group], ret_val)

                        else:
                            ret_val = "{} {}".format(self.arabicGroup[group],
                                                     ret_val)
                ret_val = "{} {}".format(group_description, ret_val)
            group += 1
        formatted_number = ""
        if self.arabicPrefixText != "":
            formatted_number += "{} ".format(self.arabicPrefixText)
        formatted_number += ret_val
        if self.integer_value != 0:
            remaining100 = int(self.integer_value % 100)

            if remaining100 == 0:
                formatted_number += self.currency_unit[0]
            elif remaining100 == 1:
                formatted_number += self.currency_unit[0]
            elif remaining100 == 2:
                if self.integer_value == 2:
                    formatted_number += self.currency_unit[1]
                else:
                    formatted_number += self.currency_unit[0]
            elif 3 <= remaining100 <= 10:
                formatted_number += self.currency_unit[2]
            elif 11 <= remaining100 <= 99:
                formatted_number += self.currency_unit[3]
        if self._decimalValue != 0:
            formatted_number += " {} ".format(self.separator)
            formatted_number += decimal_string

        if self._decimalValue != 0:
            formatted_number += " "
            remaining100 = int(self._decimalValue % 100)

            if remaining100 == 0:
                formatted_number += self.currency_subunit[0]
            elif remaining100 == 1:
                formatted_number += self.currency_subunit[0]
            elif remaining100 == 2:
                formatted_number += self.currency_subunit[1]
            elif 3 <= remaining100 <= 10:
                formatted_number += self.currency_subunit[2]
            elif 11 <= remaining100 <= 99:
                formatted_number += self.currency_subunit[3]

        if self.arabicSuffixText != "":
            formatted_number += " {}".format(self.arabicSuffixText)

        return formatted_number

    def validate_number(self, number):
        if number >= self.max_num:
            raise OverflowError(self.errmsg_too_big)
        return number

    def set_currency_prefer(self, currency):
        if currency == 'EGP':
            self.currency_unit = CURRENCY_EGP[0]
            self.currency_subunit = CURRENCY_EGP[1]
        elif currency == 'KWD':
            self.currency_unit = CURRENCY_KWD[0]
            self.currency_subunit = CURRENCY_KWD[1]
        else:
            self.currency_unit = CURRENCY_SR[0]
            self.currency_subunit = CURRENCY_SR[1]

    def to_currency(self, value, currency='SR', prefix='', suffix=''):
        self.set_currency_prefer(currency)
        self.isCurrencyNameFeminine = False
        self.separator = "و"
        self.arabicOnes = ARABIC_ONES
        self.arabicPrefixText = prefix
        self.arabicSuffixText = suffix
        return self.convert(value=value)

    def to_ordinal(self, number, prefix=''):
        if number <= 19:
            return "{}".format(self.arabicOrdinal[number])
        if number < 100:
            self.isCurrencyNameFeminine = True
        else:
            self.isCurrencyNameFeminine = False
        self.currency_subunit = ('', '', '', '')
        self.currency_unit = ('', '', '', '')
        self.arabicPrefixText = prefix
        self.arabicSuffixText = ""
        return "{}".format(self.convert(abs(number)).strip())

    def to_year(self, value):
        value = self.validate_number(value)
        return self.to_cardinal(value)

    def to_ordinal_num(self, value):
        return self.to_ordinal(value).strip()

    def to_cardinal(self, number):
        number = self.validate_number(number)
        minus = ''
        if number < 0:
            minus = 'سالب '
        self.separator = ','
        self.currency_subunit = ('', '', '', '')
        self.currency_unit = ('', '', '', '')
        self.arabicPrefixText = ""
        self.arabicSuffixText = ""
        self.arabicOnes = ARABIC_ONES
        return minus + self.convert(value=abs(number)).strip()
