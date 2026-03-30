import decimal
import logging
import math
import re
from collections import OrderedDict
from decimal import ROUND_HALF_UP, Decimal
from num2words.lang_EU import Num2Word_EU
from math import floor

from odoo import MIN_PY_VERSION

# The following section of the code is used to monkey patch
# the Arabic class of num2words package as there are some problems
# upgrading the package to the newer version that fixed the bugs
# so a temporary fix was to patch the old version with the code
# from the new version manually.
# The code is taken from num2words package: https://github.com/savoirfairelinux/num2words


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


class Num2Word_Base:
    CURRENCY_FORMS = {}
    CURRENCY_ADJECTIVES = {}

    def __init__(self):
        self.is_title = False
        self.precision = 2
        self.exclude_title = []
        self.negword = "(-) "
        self.pointword = "(.)"
        self.errmsg_nonnum = "type: %s not in [long, int, float]"
        self.errmsg_floatord = "Cannot treat float %s as ordinal."
        self.errmsg_negord = "Cannot treat negative num %s as ordinal."
        self.errmsg_toobig = "abs(%s) must be less than %s."

        self.setup()

        # uses cards
        if any(hasattr(self, field) for field in
               ['high_numwords', 'mid_numwords', 'low_numwords']):
            self.cards = OrderedDict()
            self.set_numwords()
            self.MAXVAL = 1000 * next(iter(self.cards.keys()))

    def set_numwords(self):
        self.set_high_numwords(self.high_numwords)
        self.set_mid_numwords(self.mid_numwords)
        self.set_low_numwords(self.low_numwords)

    def set_high_numwords(self, *args):
        raise NotImplementedError

    def set_mid_numwords(self, mid):
        for key, val in mid:
            self.cards[key] = val

    def set_low_numwords(self, numwords):
        for word, n in zip(numwords, range(len(numwords) - 1, -1, -1)):
            self.cards[n] = word

    def splitnum(self, value):
        for elem in self.cards:
            if elem > value:
                continue

            out = []
            if value == 0:
                div, mod = 1, 0
            else:
                div, mod = divmod(value, elem)

            if div == 1:
                out.append((self.cards[1], 1))
            else:
                if div == value:  # The system tallies, eg Roman Numerals
                    return [(div * self.cards[elem], div * elem)]
                out.append(self.splitnum(div))

            out.append((self.cards[elem], elem))

            if mod:
                out.append(self.splitnum(mod))

            return out

    def parse_minus(self, num_str):
        """Detach minus and return it as symbol with new num_str."""
        if num_str.startswith('-'):
            # Extra spacing to compensate if there is no minus.
            return '%s ' % self.negword.strip(), num_str[1:]
        return '', num_str

    def str_to_number(self, value):
        return Decimal(value)

    def to_cardinal(self, value):
        try:
            assert int(value) == value
        except (ValueError, TypeError, AssertionError):
            return self.to_cardinal_float(value)

        out = ""
        if value < 0:
            value = abs(value)
            out = "%s " % self.negword.strip()

        if value >= self.MAXVAL:
            raise OverflowError(self.errmsg_toobig % (value, self.MAXVAL))

        val = self.splitnum(value)
        words, _ = self.clean(val)
        return self.title(out + words)

    def float2tuple(self, value):
        pre = int(value)

        # Simple way of finding decimal places to update the precision
        self.precision = abs(Decimal(str(value)).as_tuple().exponent)

        post = abs(value - pre) * 10**self.precision
        if abs(round(post) - post) < 0.01:
            # We generally floor all values beyond our precision (rather than
            # rounding), but in cases where we have something like 1.239999999,
            # which is probably due to python's handling of floats, we actually
            # want to consider it as 1.24 instead of 1.23
            post = int(round(post))
        else:
            post = int(math.floor(post))

        return pre, post

    def to_cardinal_float(self, value):
        try:
            float(value) == value
        except (ValueError, TypeError, AssertionError, AttributeError):
            raise TypeError(self.errmsg_nonnum % value)

        pre, post = self.float2tuple(float(value))

        post = str(post)
        post = '0' * (self.precision - len(post)) + post

        out = [self.to_cardinal(pre)]
        if self.precision:
            out.append(self.title(self.pointword))

        for i in range(self.precision):
            curr = int(post[i])
            out.append(to_s(self.to_cardinal(curr)))

        return " ".join(out)

    def merge(self, left, right):
        raise NotImplementedError

    def clean(self, val):
        out = val
        while len(val) != 1:
            out = []
            left, right = val[:2]
            if isinstance(left, tuple) and isinstance(right, tuple):
                out.append(self.merge(left, right))
                if val[2:]:
                    out.append(val[2:])
            else:
                for elem in val:
                    if isinstance(elem, list):
                        if len(elem) == 1:
                            out.append(elem[0])
                        else:
                            out.append(self.clean(elem))
                    else:
                        out.append(elem)
            val = out
        return out[0]

    def title(self, value):
        if self.is_title:
            out = []
            value = value.split()
            for word in value:
                if word in self.exclude_title:
                    out.append(word)
                else:
                    out.append(word[0].upper() + word[1:])
            value = " ".join(out)
        return value

    def verify_ordinal(self, value):
        if not value == int(value):
            raise TypeError(self.errmsg_floatord % value)
        if not abs(value) == value:
            raise TypeError(self.errmsg_negord % value)

    def to_ordinal(self, value):
        return self.to_cardinal(value)

    def to_ordinal_num(self, value):
        return value

    # Trivial version
    def inflect(self, value, text):
        text = text.split("/")
        if value == 1:
            return text[0]
        return "".join(text)

    # //CHECK: generalise? Any others like pounds/shillings/pence?
    def to_splitnum(self, val, hightxt="", lowtxt="", jointxt="",
                    divisor=100, longval=True, cents=True):
        out = []

        if isinstance(val, float):
            high, low = self.float2tuple(val)
        else:
            try:
                high, low = val
            except TypeError:
                high, low = divmod(val, divisor)

        if high:
            hightxt = self.title(self.inflect(high, hightxt))
            out.append(self.to_cardinal(high))
            if low:
                if longval:
                    if hightxt:
                        out.append(hightxt)
                    if jointxt:
                        out.append(self.title(jointxt))
            elif hightxt:
                out.append(hightxt)

        if low:
            if cents:
                out.append(self.to_cardinal(low))
            else:
                out.append("%02d" % low)
            if lowtxt and longval:
                out.append(self.title(self.inflect(low, lowtxt)))

        return " ".join(out)

    def to_year(self, value, **kwargs):
        return self.to_cardinal(value)

    def pluralize(self, n, forms):
        """
        Should resolve gettext form:
        http://docs.translatehouse.org/projects/localization-guide/en/latest/l10n/pluralforms.html
        """
        raise NotImplementedError

    def _money_verbose(self, number, currency):
        return self.to_cardinal(number)

    def _cents_verbose(self, number, currency):
        return self.to_cardinal(number)

    def _cents_terse(self, number, currency):
        return "%02d" % number

    def to_currency(self, val, currency='EUR', cents=True, separator=',',
                    adjective=False):
        """
        Args:
            val: Numeric value
            currency (str): Currency code
            cents (bool): Verbose cents
            separator (str): Cent separator
            adjective (bool): Prefix currency name with adjective
        Returns:
            str: Formatted string

        """
        left, right, is_negative = parse_currency_parts(val)

        try:
            cr1, cr2 = self.CURRENCY_FORMS[currency]

        except KeyError:
            raise NotImplementedError(
                'Currency code "%s" not implemented for "%s"' %
                (currency, self.__class__.__name__))

        if adjective and currency in self.CURRENCY_ADJECTIVES:
            cr1 = prefix_currency(self.CURRENCY_ADJECTIVES[currency], cr1)

        minus_str = "%s " % self.negword.strip() if is_negative else ""
        money_str = self._money_verbose(left, currency)
        cents_str = self._cents_verbose(right, currency) \
            if cents else self._cents_terse(right, currency)

        return '%s%s %s%s %s %s' % (
            minus_str,
            money_str,
            self.pluralize(left, cr1),
            separator,
            cents_str,
            self.pluralize(right, cr2)
        )

    def setup(self):
        pass


class Num2Word_AR_Fixed(Num2Word_Base):
    errmsg_toobig = "abs(%s) must be less than %s."
    MAXVAL = 10**51

    def __init__(self):
        super().__init__()

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
            "كوينتليونا", "سكستيليونا", "سبتيليونا", "أوكتيليونا ",
            "نونيليونا", "ديسيليونا", "أندسيليونا", "دوديسيليونا",
            "تريديسيليونا", "كوادريسيليونا", "كوينتينيليونا"
        ]
        self.arabicTwos = [
            "مئتان", "ألفان", "مليونان", "ملياران", "تريليونان",
            "كوادريليونان", "كوينتليونان", "سكستيليونان", "سبتيليونان",
            "أوكتيليونان ", "نونيليونان ", "ديسيليونان", "أندسيليونان",
            "دوديسيليونان", "تريديسيليونان", "كوادريسيليونان", "كوينتينيليونان"
        ]
        self.arabicGroup = [
            "مائة", "ألف", "مليون", "مليار", "تريليون", "كوادريليون",
            "كوينتليون", "سكستيليون", "سبتيليون", "أوكتيليون", "نونيليون",
            "ديسيليون", "أندسيليون", "دوديسيليون", "تريديسيليون",
            "كوادريسيليون", "كوينتينيليون"
        ]
        self.arabicAppendedGroup = [
            "", "ألفاً", "مليوناً", "ملياراً", "تريليوناً", "كوادريليوناً",
            "كوينتليوناً", "سكستيليوناً", "سبتيليوناً", "أوكتيليوناً",
            "نونيليوناً", "ديسيليوناً", "أندسيليوناً", "دوديسيليوناً",
            "تريديسيليوناً", "كوادريسيليوناً", "كوينتينيليوناً"
        ]
        self.arabicPluralGroups = [
            "", "آلاف", "ملايين", "مليارات", "تريليونات", "كوادريليونات",
            "كوينتليونات", "سكستيليونات", "سبتيليونات", "أوكتيليونات",
            "نونيليونات", "ديسيليونات", "أندسيليونات", "دوديسيليونات",
            "تريديسيليونات", "كوادريسيليونات", "كوينتينيليونات"
        ]
        assert len(self.arabicAppendedGroup) == len(self.arabicGroup)
        assert len(self.arabicPluralGroups) == len(self.arabicGroup)
        assert len(self.arabicAppendedTwos) == len(self.arabicTwos)

    def number_to_arabic(self, arabic_prefix_text, arabic_suffix_text):
        self.arabicPrefixText = arabic_prefix_text
        self.arabicSuffixText = arabic_suffix_text
        self.extract_integer_and_decimal_parts()

    def extract_integer_and_decimal_parts(self):
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
            for _ in range(0, self.partPrecision - decimal_part_length):
                decimal_part_builder += '0'
            decimal_part = decimal_part_builder

            if len(decimal_part) <= self.partPrecision:
                dec = len(decimal_part)
            else:
                dec = self.partPrecision
            result = decimal_part[0: dec]
        else:
            result = decimal_part

        # The following is useless (never happens)
        # for i in range(len(result), self.partPrecision):
        #     result += '0'
        return result

    def digit_feminine_status(self, digit, group_level):
        if group_level == -1:
            if self.isCurrencyPartNameFeminine:
                return self.arabicFeminineOnes[int(digit)]
            else:
                # Note: this never happens
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
                ret_val = f"{self.arabicAppendedTwos[0]}"
            else:
                ret_val = f"{self.arabicHundreds[int(hundreds)]}"
                if ret_val and tens != 0:
                    ret_val += " و "

        if tens > 0:
            if tens < 20:
                # if int(group_level) >= len(self.arabicTwos):
                #     raise OverflowError(self.errmsg_toobig %
                #                         (self.number, self.MAXVAL))
                assert int(group_level) < len(self.arabicTwos)
                if tens == 2 and int(hundreds) == 0 and group_level > 0:
                    power = int(math.log10(self.integer_value))
                    if self.integer_value > 10 and power % 3 == 0 and \
                            self.integer_value == 2 * (10 ** power):
                        ret_val = f"{self.arabicAppendedTwos[int(group_level)]}"
                    else:
                        ret_val = f"{self.arabicTwos[int(group_level)]}"
                else:
                    if tens == 1 and group_level > 0 and hundreds == 0:
                        # Note: this never happens
                        # (hundreds == 0 only if group_number is 0)
                        ret_val += ""
                    elif (tens == 1 or tens == 2) and (
                            group_level == 0 or group_level == -1) and \
                            hundreds == 0 and remaining_number == 0:
                        # Note: this never happens (idem)
                        ret_val += ""
                    elif tens == 1 and group_level > 0:
                        ret_val += self.arabicGroup[int(group_level)]
                    else:
                        ret_val += self.digit_feminine_status(int(tens),
                                                              group_level)
            else:
                ones = tens % 10
                tens = (tens / 10) - 2
                if ones > 0:
                    ret_val += self.digit_feminine_status(ones, group_level)
                if ret_val and ones != 0:
                    ret_val += " و "

                ret_val += self.arabicTens[int(tens)]

        return ret_val

    # We use this instead of built-in `abs` function,
    # because `abs` suffers from loss of precision for big numbers
    def absolute(self, number):
        return number if number >= 0 else -number

    # We use this instead of `"{:09d}".format(number)`,
    # because the string conversion suffers from loss of
    # precision for big numbers
    def to_str(self, number):
        integer = int(number)
        if integer == number:
            return str(integer)
        decimal = round((number - integer) * 10**9)
        return f"{integer}.{decimal:09d}"

    def convert(self, value):
        self.number = self.to_str(value)
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

            temp_number_dec = Decimal(str(temp_number))
            try:
                number_to_process = int(temp_number_dec % Decimal(str(1000)))
            except decimal.InvalidOperation:
                decimal.getcontext().prec = len(
                    temp_number_dec.as_tuple().digits
                )
                number_to_process = int(temp_number_dec % Decimal(str(1000)))

            temp_number = int(temp_number_dec / Decimal(1000))

            group_description = \
                self.process_arabic_group(number_to_process,
                                          group,
                                          Decimal(floor(temp_number)))
            if group_description:
                if group > 0:
                    if ret_val:
                        ret_val = f"و {ret_val}"
                    if number_to_process != 2 and number_to_process != 1:
                        # if group >= len(self.arabicGroup):
                        #     raise OverflowError(self.errmsg_toobig %
                        #                         (self.number, self.MAXVAL)
                        #     )
                        assert group < len(self.arabicGroup)
                        if number_to_process % 100 != 1:
                            if 3 <= number_to_process <= 10:
                                ret_val = f"{self.arabicPluralGroups[group]} {ret_val}"
                            else:
                                if ret_val:
                                    ret_val = f"{self.arabicAppendedGroup[group]} {ret_val}"
                                else:
                                    ret_val = f"{self.arabicGroup[group]} {ret_val}"

                        else:
                            ret_val = f"{self.arabicGroup[group]} {ret_val}"

                ret_val = f"{group_description} {ret_val}"
            group += 1
        formatted_number = ""
        if self.arabicPrefixText:
            formatted_number += f"{self.arabicPrefixText} "
        formatted_number += ret_val
        if self.integer_value != 0:
            remaining100 = int(self.integer_value % 100)

            if remaining100 == 0 or remaining100 == 1:
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
            formatted_number += f" {self.separator} "
            formatted_number += decimal_string

        if self._decimalValue != 0:
            formatted_number += " "
            remaining100 = int(self._decimalValue % 100)

            if remaining100 == 0 or remaining100 == 1:
                formatted_number += self.currency_subunit[0]
            elif remaining100 == 2:
                formatted_number += self.currency_subunit[1]
            elif 3 <= remaining100 <= 10:
                formatted_number += self.currency_subunit[2]
            elif 11 <= remaining100 <= 99:
                formatted_number += self.currency_subunit[3]

        if self.arabicSuffixText:
            formatted_number += f" {self.arabicSuffixText}"

        return formatted_number

    def validate_number(self, number):
        if number >= self.MAXVAL:
            raise OverflowError(self.errmsg_toobig % (number, self.MAXVAL))
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
            return f"{self.arabicOrdinal[number]}"
        if number < 100:
            self.isCurrencyNameFeminine = True
        else:
            self.isCurrencyNameFeminine = False
        self.currency_subunit = ('', '', '', '')
        self.currency_unit = ('', '', '', '')
        self.arabicPrefixText = prefix
        self.arabicSuffixText = ""
        return f"{self.convert(self.absolute(number)).strip()}"

    def to_year(self, value):
        value = self.validate_number(value)
        return self.to_cardinal(value)

    def to_ordinal_num(self, value):
        return self.to_ordinal(value).strip()

    def to_cardinal(self, number):
        self.isCurrencyNameFeminine = False
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
        return minus + self.convert(value=self.absolute(number)).strip()


def parse_currency_parts(value, is_int_with_cents=True):
    if isinstance(value, int):
        if is_int_with_cents:
            # assume cents if value is integer
            negative = value < 0
            value = abs(value)
            integer, cents = divmod(value, 100)
        else:
            negative = value < 0
            integer, cents = abs(value), 0

    else:
        value = Decimal(value)
        value = value.quantize(
            Decimal('.01'),
            rounding=ROUND_HALF_UP
        )
        negative = value < 0
        value = abs(value)
        integer, fraction = divmod(value, 1)
        integer = int(integer)
        cents = int(fraction * 100)

    return integer, cents, negative


def prefix_currency(prefix, base):
    return tuple("%s %s" % (prefix, i) for i in base)


try:
    strtype = basestring
except NameError:
    strtype = str


def to_s(val):
    try:
        return unicode(val)
    except NameError:
        return str(val)


# Derived from num2cyrillic licensed under LGPL-3.0-only
# Copyright 2018  ClaimCompass, Inc (num2cyrillic authored by Velizar Shulev) https://github.com/ClaimCompass/num2cyrillic
# Copyright 1997 The PHP Group (PEAR::Numbers_Words, authored by Kouber Saparev) https://github.com/pear/Numbers_Words/blob/master/Numbers/Words/Locale/bg.php


class NumberToWords_BG(Num2Word_Base):
    locale = 'bg'
    lang = 'Bulgarian'
    lang_native = 'Български'
    _misc_strings = {
        'deset': 'десет',
        'edinadeset': 'единадесет',
        'na': 'на',
        'sto': 'сто',
        'sta': 'ста',
        'stotin': 'стотин',
        'hiliadi': 'хиляди',
    }
    _digits = {
        0: [None, 'едно', 'две', 'три', 'четири', 'пет', 'шест', 'седем', 'осем', 'девет'],
    }
    _digits[1] = [None, 'един', 'два'] + _digits[0][3:]
    _digits[-1] = [None, 'една'] + _digits[0][2:]
    _last_and = False
    _zero = 'нула'
    _infinity = 'безкрайност'
    _and = 'и'
    _sep = ' '
    _minus = 'минус'
    _plural = 'а'
    _exponent = {
        0: '',
        3: 'хиляда',
        6: 'милион',
        9: 'милиард',
        12: 'трилион',
        15: 'квадрилион',
        18: 'квинтилион',
        21: 'секстилион',
        24: 'септилион',
        27: 'октилион',
        30: 'ноналион',
        33: 'декалион',
        36: 'ундекалион',
        39: 'дуодекалион',
        42: 'тредекалион',
        45: 'кватордекалион',
        48: 'квинтдекалион',
        51: 'сексдекалион',
        54: 'септдекалион',
        57: 'октодекалион',
        60: 'новемдекалион',
        63: 'вигинтилион',
        66: 'унвигинтилион',
        69: 'дуовигинтилион',
        72: 'тревигинтилион',
        75: 'кваторвигинтилион',
        78: 'квинвигинтилион',
        81: 'сексвигинтилион',
        84: 'септенвигинтилион',
        87: 'октовигинтилион',
        90: 'новемвигинтилион',
        93: 'тригинтилион',
        96: 'унтригинтилион',
        99: 'дуотригинтилион',
        102: 'третригинтилион',
        105: 'кватортригинтилион',
        108: 'квинтригинтилион',
        111: 'секстригинтилион',
        114: 'септентригинтилион',
        117: 'октотригинтилион',
        120: 'новемтригинтилион',
        123: 'квадрагинтилион',
        126: 'унквадрагинтилион',
        129: 'дуоквадрагинтилион',
        132: 'треквадрагинтилион',
        135: 'кваторквадрагинтилион',
        138: 'квинквадрагинтилион',
        141: 'сексквадрагинтилион',
        144: 'септенквадрагинтилион',
        147: 'октоквадрагинтилион',
        150: 'новемквадрагинтилион',
        153: 'квинквагинтилион',
        156: 'унквинкагинтилион',
        159: 'дуоквинкагинтилион',
        162: 'треквинкагинтилион',
        165: 'кваторквинкагинтилион',
        168: 'квинквинкагинтилион',
        171: 'сексквинкагинтилион',
        174: 'септенквинкагинтилион',
        177: 'октоквинкагинтилион',
        180: 'новемквинкагинтилион',
        183: 'сексагинтилион',
        186: 'унсексагинтилион',
        189: 'дуосексагинтилион',
        192: 'тресексагинтилион',
        195: 'кваторсексагинтилион',
        198: 'квинсексагинтилион',
        201: 'секссексагинтилион',
        204: 'септенсексагинтилион',
        207: 'октосексагинтилион',
        210: 'новемсексагинтилион',
        213: 'септагинтилион',
        216: 'унсептагинтилион',
        219: 'дуосептагинтилион',
        222: 'тресептагинтилион',
        225: 'кваторсептагинтилион',
        228: 'квинсептагинтилион',
        231: 'секссептагинтилион',
        234: 'септенсептагинтилион',
        237: 'октосептагинтилион',
        240: 'новемсептагинтилион',
        243: 'октогинтилион',
        246: 'уноктогинтилион',
        249: 'дуооктогинтилион',
        252: 'треоктогинтилион',
        255: 'кватороктогинтилион',
        258: 'квиноктогинтилион',
        261: 'сексоктогинтилион',
        264: 'септоктогинтилион',
        267: 'октооктогинтилион',
        270: 'новемоктогинтилион',
        273: 'нонагинтилион',
        276: 'уннонагинтилион',
        279: 'дуононагинтилион',
        282: 'тренонагинтилион',
        285: 'кваторнонагинтилион',
        288: 'квиннонагинтилион',
        291: 'секснонагинтилион',
        294: 'септеннонагинтилион',
        297: 'октононагинтилион',
        300: 'новемнонагинтилион',
        303: 'центилион',
    }

    def to_cardinal(self, value):
        return '' if value is None else self._to_words(value).strip()

    def to_ordinal(self, _):
        raise NotImplementedError

    def to_ordinal_num(self, _):
        raise NotImplementedError

    def to_year(self, _):
        raise NotImplementedError

    def to_currency(self, _):
        raise NotImplementedError

    def _split_number(self, num):
        if isinstance(num, int):
            num = str(num)
        first = []
        if len(num) % 3 != 0:
            if len(num[1:]) % 3 == 0:
                first = [num[0:1]]
                num = num[1:]
            elif len(num[2:]) % 3 == 0:
                first = [num[0:2]]
                num = num[2:]
        ret = [num[i:i + 3] for i in range(0, len(num), 3)]
        return first + ret

    def _discard_empties(self, ls):
        return list(filter(lambda x: x is not None, ls))

    def _show_digits_group(self, num, gender=0, last=False):
        num = int(num)
        e = int(num % 10)                # ones
        d = int((num - e) % 100 / 10)        # tens
        s = int((num - d * 10 - e) % 1000 / 100)  # hundreds
        ret = [None] * 6

        if s:
            if s == 1:
                ret[1] = self._misc_strings['sto']
            elif s == 2 or s == 3:
                ret[1] = self._digits[0][s] + self._misc_strings['sta']
            else:
                ret[1] = self._digits[0][s] + self._misc_strings['stotin']

        if d:
            if d == 1:
                if not e:
                    ret[3] = self._misc_strings['deset']
                else:
                    if e == 1:
                        ret[3] = self._misc_strings['edinadeset']
                    else:
                        ret[3] = self._digits[1][e] + self._misc_strings['na'] + self._misc_strings['deset']
                    e = 0
            else:
                ret[3] = self._digits[1][d] + self._misc_strings['deset']

        if e:
            ret[5] = self._digits[gender][e]

        if len(self._discard_empties(ret)) > 1:
            if e:
                ret[4] = self._and
            else:
                ret[2] = self._and

        if last:
            if not s or len(self._discard_empties(ret)) == 1:
                ret[0] = self._and
            self._last_and = True

        return self._sep.join(self._discard_empties(ret))

    def _to_words(self, num=0):
        num_groups = self._split_number(num)
        sizeof_num_groups = len(num_groups)

        ret = [None] * (sizeof_num_groups + 1)
        ret_minus = ''

        if num < 0:
            ret_minus = self._minus + self._sep
        elif num == 0:
            return self._zero

        i = sizeof_num_groups - 1
        j = 1
        while i >= 0:
            if ret[j] is None:
                ret[j] = ''

            _pow = sizeof_num_groups - i

            if num_groups[i] != '000':
                if int(num_groups[i]) > 1:
                    if _pow == 1:
                        ret[j] += self._show_digits_group(num_groups[i], 0, not self._last_and and i) + self._sep
                        ret[j] += self._exponent[(_pow - 1) * 3]
                    elif _pow == 2:
                        ret[j] += self._show_digits_group(num_groups[i], -1, not self._last_and and i) + self._sep
                        ret[j] += self._misc_strings['hiliadi'] + self._sep
                    else:
                        ret[j] += self._show_digits_group(num_groups[i], 1, not self._last_and and i) + self._sep
                        ret[j] += self._exponent[(_pow - 1) * 3] + self._plural + self._sep
                else:
                    if _pow == 1:
                        ret[j] += self._show_digits_group(num_groups[i], 0, not self._last_and and i) + self._sep
                    elif _pow == 2:
                        ret[j] += self._exponent[(_pow - 1) * 3] + self._sep
                    else:
                        ret[j] += self._digits[1][1] + self._sep + self._exponent[(_pow - 1) * 3] + self._sep

            i -= 1
            j += 1

        ret = self._discard_empties(ret)
        ret.reverse()
        return ret_minus + ''.join(ret)


class NumberToWords_CA(Num2Word_EU):
    # This section is about implementing catalan language as current versions of num2words
    # used by Odoo (0.5.10/13) are not supporting it yet
    # code is taken from num2words 0.5.14: https://github.com/savoirfairelinux/num2words/blob/master/num2words/lang_CA.py
    GENERIC_DOLLARS = ('dòlar', 'dòlars')
    GENERIC_CENTS = ('centau', 'centaus')
    CURRENCIES_UNA = (
        'SLL',
        'SEK',
        'NOK',
        'CZK',
        'DKK',
        'ISK',
        'SKK',
        'GBP',
        'CYP',
        'EGP',
        'FKP',
        'GIP',
        'LBP',
        'SDG',
        'SHP',
        'SSP',
        'SYP',
        'INR',
        'IDR',
        'LKR',
        'MUR',
        'NPR',
        'PKR',
        'SCR',
        'ESP',
        'TRY',
        'ITL',
    )
    CENTS_UNA = ('EGP', 'JOD', 'LBP', 'SDG', 'SSP', 'SYP')

    CURRENCY_FORMS = {
        'EUR': (('euro', 'euros'), ('cèntim', 'cèntims')),
        'ESP': (('pesseta', 'pessetes'), ('cèntim', 'cèntims')),
        'USD': (GENERIC_DOLLARS, ('centau', 'centaus')),
        'PEN': (('sol', 'sols'), ('cèntim', 'cèntims')),
        'CRC': (('colón', 'colons'), GENERIC_CENTS),
        'AUD': (GENERIC_DOLLARS, GENERIC_CENTS),
        'CAD': (GENERIC_DOLLARS, GENERIC_CENTS),
        'GBP': (('lliura', 'lliures'), ('penic', 'penics')),
        'RUB': (('ruble', 'rubles'), ('copec', 'copecs')),
        'SEK': (('corona', 'corones'), ('öre', 'öre')),
        'NOK': (('corona', 'corones'), ('øre', 'øre')),
        'PLN': (('zloty', 'zlotys'), ('grosz', 'groszy')),
        'MXN': (('peso', 'pesos'), GENERIC_CENTS),
        'RON': (('leu', 'lei'), ('ban', 'bani')),
        'INR': (('rupia', 'rupies'), ('paisa', 'paise')),
        'HUF': (('fòrint', 'fòrints'), ('fillér', 'fillérs')),
        'FRF': (('franc', 'francs'), ('cèntim', 'cèntims')),
        'CNY': (('iuan', 'iuans'), ('fen', 'jiao')),
        'CZK': (('corona', 'corones'), ('haléř', 'haléřů')),
        'NIO': (('córdoba', 'córdobas'), GENERIC_CENTS),
        'VES': (('bolívar', 'bolívars'), ('cèntim', 'cèntims')),
        'BRL': (('real', 'reals'), GENERIC_CENTS),
        'CHF': (('franc', 'francs'), ('cèntim', 'cèntims')),
        'JPY': (('ien', 'iens'), ('sen', 'sen')),
        'KRW': (('won', 'wons'), ('jeon', 'jeon')),
        'KPW': (('won', 'wons'), ('chŏn', 'chŏn')),
        'TRY': (('lira', 'lires'), ('kuruş', 'kuruş')),
        'ZAR': (('rand', 'rands'), ('cèntim', 'cèntims')),
        'KZT': (('tenge', 'tenge'), ('tin', 'tin')),
        'UAH': (('hrívnia', 'hrívnies'), ('kopiika', 'kopíok')),
        'THB': (('baht', 'bahts'), ('satang', 'satang')),
        'AED': (('dirham', 'dirhams'), ('fils', 'fulūs')),
        'AFN': (('afgani', 'afganis'), ('puli', 'puls')),
        'ALL': (('lek', 'lekë'), ('qqindarka', 'qindarkë')),
        'AMD': (('dram', 'drams'), ('luma', 'lumas')),
        'ANG': (('florí', 'florins'), ('cèntim', 'cèntims')),
        'AOA': (('kwanza', 'kwanzes'), ('cèntim', 'cèntims')),
        'ARS': (('peso', 'pesos'), GENERIC_CENTS),
        'AWG': (('florí', 'florins'), GENERIC_CENTS),
        'AZN': (('manat', 'manats'), ('qəpik', 'qəpik')),
        'BBD': (GENERIC_DOLLARS, GENERIC_CENTS),
        'BDT': (('taka', 'taka'), ('poisha', 'poisha')),
        'BGN': (('lev', 'leva'), ('stotinka', 'stotinki')),
        'BHD': (('dinar', 'dinars'), ('fils', 'fulūs')),
        'BIF': (('franc', 'francs'), ('cèntim', 'cèntims')),
        'BMD': (GENERIC_DOLLARS, GENERIC_CENTS),
        'BND': (GENERIC_DOLLARS, GENERIC_CENTS),
        'BOB': (('boliviano', 'bolivianos'), GENERIC_CENTS),
        'BSD': (GENERIC_DOLLARS, GENERIC_CENTS),
        'BTN': (('ngultrum', 'ngultrums'), ('chetrum', 'chetrums')),
        'BWP': (('pula', 'pula'), ('thebe', 'thebe')),
        'BYN': (('ruble', 'rubles'), ('copec', 'copecs')),
        'BYR': (('ruble', 'rubles'), ('copec', 'copecs')),
        'BZD': (GENERIC_DOLLARS, ('cèntim', 'cèntims')),
        'CDF': (('franc', 'francs'), ('cèntim', 'cèntims')),
        'CLP': (('peso', 'pesos'), GENERIC_CENTS),
        'COP': (('peso', 'pesos'), GENERIC_CENTS),
        'CUP': (('peso', 'pesos'), GENERIC_CENTS),
        'CVE': (('escut', 'escuts'), GENERIC_CENTS),
        'CYP': (('lliura', 'lliures'), ('cèntim', 'cèntims')),
        'DJF': (('franc', 'francs'), ('cèntim', 'cèntims')),
        'DKK': (('corona', 'corones'), ('øre', 'øre')),
        'DOP': (('peso', 'pesos'), GENERIC_CENTS),
        'DZD': (('dinar', 'dinars'), ('cèntim', 'cèntims')),
        'ECS': (('sucre', 'sucres'), GENERIC_CENTS),
        'EGP': (('lliura', 'lliures'), ('piastre', 'piastres')),
        'ERN': (('nakfa', 'nakfes'), ('cèntim', 'cèntims')),
        'ETB': (('birr', 'birr'), ('cèntim', 'cèntims')),
        'FJD': (GENERIC_DOLLARS, GENERIC_CENTS),
        'FKP': (('lliura', 'lliures'), ('penic', 'penics')),
        'GEL': (('lari', 'laris'), ('tetri', 'tetri')),
        'GHS': (('cedi', 'cedis'), ('pesewa', 'pesewas')),
        'GIP': (('lliura', 'lliures'), ('penic', 'penics')),
        'GMD': (('dalasi', 'dalasis'), ('butut', 'bututs')),
        'GNF': (('franc', 'francs'), ('cèntim', 'cèntims')),
        'GTQ': (('quetzal', 'quetzals'), GENERIC_CENTS),
        'GYD': (GENERIC_DOLLARS, GENERIC_CENTS),
        'HKD': (GENERIC_DOLLARS, GENERIC_CENTS),
        'HNL': (('lempira', 'lempires'), GENERIC_CENTS),
        'HRK': (('kuna', 'kuna'), ('lipa', 'lipa')),
        'HTG': (('gourde', 'gourdes'), ('cèntim', 'cèntims')),
        'IDR': (('rúpia', 'rúpies'), ('cèntim', 'cèntims')),
        'ILS': (('xéquel', 'xéquels'), ('agorà', 'agorot')),
        'IQD': (('dinar', 'dinars'), ('fils', 'fils')),
        'IRR': (('rial', 'rials'), ('dinar', 'dinars')),
        'ISK': (('corona', 'corones'), ('eyrir', 'aurar')),
        'ITL': (('lira', 'lires'), ('cèntim', 'cèntims')),
        'JMD': (GENERIC_DOLLARS, ('cèntim', 'cèntims')),
        'JOD': (('dinar', 'dinars'), ('piastra', 'piastres')),
        'KES': (('xiling', 'xílings'), ('cèntim', 'cèntims')),
        'KGS': (('som', 'som'), ('tyiyn', 'tyiyn')),
        'KHR': (('riel', 'riels'), ('cèntim', 'cèntims')),
        'KMF': (('franc', 'francs'), ('cèntim', 'cèntims')),
        'KWD': (('dinar', 'dinars'), ('fils', 'fils')),
        'KYD': (GENERIC_DOLLARS, ('cèntim', 'cèntims')),
        'LAK': (('kip', 'kips'), ('at', 'at')),
        'LBP': (('lliura', 'lliures'), ('piastra', 'piastres')),
        'LKR': (('rúpia', 'rúpies'), ('cèntim', 'cèntims')),
        'LRD': (GENERIC_DOLLARS, ('cèntim', 'cèntims')),
        'LSL': (('loti', 'maloti'), ('sente', 'lisente')),
        'LTL': (('lita', 'litai'), ('cèntim', 'cèntims')),
        'LYD': (('dinar', 'dinars'), ('dírham', 'dírhams')),
        'MAD': (('dírham', 'dirhams'), ('cèntim', 'cèntims')),
        'MDL': (('leu', 'lei'), ('ban', 'bani')),
        'MGA': (('ariary', 'ariary'), ('iraimbilanja', 'iraimbilanja')),
        'MKD': (('denar', 'denari'), ('deni', 'deni')),
        'MMK': (('kyat', 'kyats'), ('pya', 'pyas')),
        'MNT': (('tögrög', 'tögrög'), ('möngö', 'möngö')),
        'MOP': (('pataca', 'pataques'), ('avo', 'avos')),
        'MRO': (('ouguiya', 'ouguiya'), ('khoums', 'khoums')),
        'MRU': (('ouguiya', 'ouguiya'), ('khoums', 'khoums')),
        'MUR': (('rupia', 'rúpies'), ('cèntim', 'cèntims')),
        'MVR': (('rufiyaa', 'rufiyaa'), ('laari', 'laari')),
        'MWK': (('kwacha', 'kwacha'), ('tambala', 'tambala')),
        'MYR': (('ringgit', 'ringgits'), ('sen', 'sens')),
        'MZN': (('metical', 'meticals'), GENERIC_CENTS),
        'NAD': (GENERIC_DOLLARS, ('cèntim', 'cèntims')),
        'NGN': (('naira', 'naires'), ('kobo', 'kobos')),
        'NPR': (('rupia', 'rupies'), ('paisa', 'paises')),
        'NZD': (GENERIC_DOLLARS, GENERIC_CENTS),
        'OMR': (('rial', 'rials'), ('baisa', 'baisa')),
        'PAB': (GENERIC_DOLLARS, ('centésimo', 'centésimos')),
        'PGK': (('kina', 'kina'), ('toea', 'toea')),
        'PHP': (('peso', 'pesos'), GENERIC_CENTS),
        'PKR': (('rupia', 'rupies'), ('paisa', 'paise')),
        'PLZ': (('zloty', 'zlotys'), ('grosz', 'groszy')),
        'PYG': (('guaraní', 'guaranís'), ('cèntim', 'cèntims')),
        'QAR': (('rial', 'rials'), ('dírham', 'dírhams')),
        'QTQ': (('quetzal', 'quetzals'), GENERIC_CENTS),
        'RSD': (('dinar', 'dinars'), ('para', 'para')),
        'RUR': (('ruble', 'rubles'), ('copec', 'copecs')),
        'RWF': (('franc', 'francs'), ('cèntim', 'cèntims')),
        'SAR': (('riyal', 'riyals'), ('hàl·lala', 'hàl·lalat')),
        'SBD': (GENERIC_DOLLARS, ('cèntim', 'cèntims')),
        'SCR': (('rupia', 'rupies'), ('cèntim', 'cèntims')),
        'SDG': (('lliura', 'lliures'), ('piastre', 'piastres')),
        'SGD': (GENERIC_DOLLARS, ('cèntim', 'cèntims')),
        'SHP': (('lliura', 'lliures'), ('penic', 'penics')),
        'SLL': (('leonE', 'leones'), ('cèntim', 'cèntims')),
        'SRD': (GENERIC_DOLLARS, ('cèntim', 'cèntims')),
        'SSP': (('lliura', 'lliures'), ('piastre', 'piastres')),
        'STD': (('dobra', 'dobrAs'), ('cèntim', 'cèntims')),
        'SVC': (('colón', 'colons'), GENERIC_CENTS),
        'SYP': (('lliura', 'lliures'), ('piastre', 'piastres')),
        'SZL': (('lilangeni', 'emalangeni'), ('cèntim', 'cèntims')),
        'TJS': (('somoni', 'somoni'), ('diram', 'diram')),
        'TMT': (('manat', 'manats'), ('teňňesi', 'teňňesi')),
        'TND': (('dinar', 'dinars'), ('mil·lim', 'mil·limat')),
        'TOP': (('paanga', 'paangas'), ('seniti', 'seniti')),
        'TTD': (GENERIC_DOLLARS, ('cèntim', 'cèntims')),
        'TWD': (('nou dòlar', 'nous dòlars'), ('fen', 'fen')),
        'TZS': (('xíling', 'xílings'), ('cèntim', 'cèntims')),
        'UGX': (('xíling', 'xílings'), ('cèntim', 'cèntims')),
        'UYU': (('peso', 'pesos'), ('centèsim', 'centèsims')),
        'UZS': (('som', 'som'), ('tiyin', 'tiyin')),
        'VND': (('dong', 'dongs'), ('xu', 'xu')),
        'VUV': (('vatu', 'vatus'), ('cèntim', 'cèntims')),
        'WST': (('tala', 'tala'), ('sene', 'sene')),
        'XAF': (('franc CFA', 'francs CFA'), ('cèntim', 'cèntims')),
        'XCD': (GENERIC_DOLLARS, ('cèntim', 'cèntims')),
        'XOF': (('franc CFA', 'francs CFA'), ('cèntim', 'cèntims')),
        'XPF': (('franc CFP', 'francs CFP'), ('cèntim', 'cèntims')),
        'YER': (('rial', 'rials'), ('fils', 'fils')),
        'YUM': (('dinar', 'dinars'), ('para', 'para')),
        'ZMW': (('kwacha', 'kwacha'), ('ngwee', 'ngwee')),
        'ZWL': (GENERIC_DOLLARS, ('cèntim', 'cèntims')),
    }

    GIGA_SUFFIX = None
    MEGA_SUFFIX = "ilió"

    def setup(self):
        lows = ["quadr", "tr", "b", "m"]
        self.high_numwords = self.gen_high_numwords([], [], lows)
        self.negword = "menys "
        self.pointword = "punt"
        self.errmsg_nonnum = "type(%s) no és [long, int, float]"
        self.errmsg_floatord = (
            "El float %s no pot ser tractat com un"
            " ordinal."
        )
        self.errmsg_negord = (
            "El número negatiu %s no pot ser tractat"
            " com un ordinal."
        )
        self.errmsg_toobig = "abs(%s) ha de ser inferior a %s."
        self.gender_stem = "è"
        self.exclude_title = ["i", "menys", "punt"]

        self.mid_numwords = [
            (1000, "mil"),
            (100, "cent"),
            (90, "noranta"),
            (80, "vuitanta"),
            (70, "setanta"),
            (60, "seixanta"),
            (50, "cinquanta"),
            (40, "quaranta"),
            (30, "trenta"),
        ]
        self.low_numwords = [
            "vint-i-nou",
            "vint-i-vuit",
            "vint-i-set",
            "vint-i-sis",
            "vint-i-cinc",
            "vint-i-quatre",
            "vint-i-tres",
            "vint-i-dos",
            "vint-i-un",
            "vint",
            "dinou",
            "divuit",
            "disset",
            "setze",
            "quinze",
            "catorze",
            "tretze",
            "dotze",
            "onze",
            "deu",
            "nou",
            "vuit",
            "set",
            "sis",
            "cinc",
            "quatre",
            "tres",
            "dos",
            "un",
            "zero",
        ]
        self.mid_num = {
            1000: "mil",
            100: "cent",
            90: "noranta",
            80: "vuitanta",
            70: "setanta",
            60: "seixanta",
            50: "cinquanta",
            40: "quaranta",
            30: "trenta",
            20: "vint",
            10: "deu",
        }
        self.low_num = {
            0: "zero",
            1: "un",
            2: "dos",
            3: "tres",
            4: "quatre",
            5: "cinc",
            6: "sis",
            7: "set",
            8: "vuit",
            9: "nou",
            10: "deu",
            11: "onze",
            12: "dotze",
            13: "tretze",
            14: "catorze",
            15: "quinze",
            16: "setze",
            17: "disset",
            18: "divuit",
            19: "dinou",
            20: "vint",
            21: "vint-i-un",
            22: "vint-i-dos",
            23: "vint-i-tres",
            24: "vint-i-quatre",
            25: "vint-i-cinc",
            26: "vint-i-sis",
            27: "vint-i-set",
            28: "vint-i-vuit",
            29: "vint-i-nou",
        }
        self.ords = {
            1: "primer",
            2: "segon",
            3: "tercer",
            4: "quart",
            5: "cinqu",
            6: "sis",
            7: "set",
            8: "vuit",
            9: "nov",
            10: "des",
            11: "onz",
            12: "dotz",
            13: "tretz",
            14: "catorz",
            15: "quinz",
            16: "setz",
            17: "disset",
            18: "divuit",
            19: "dinov",
            20: "vint",
            30: "trent",
            40: "quarant",
            50: "cinquant",
            60: "seixant",
            70: "setant",
            80: "vuitant",
            90: "norant",
            100: "cent",
            200: "dos-cent",
            300: "tres-cent",
            400: "quatre-cent",
            500: "cinc-cent",
            600: "sis-cent",
            700: "set-cent",
            800: "vuit-cent",
            900: "nou-cent",
            1e3: "mil",
            1e6: "milion",
            1e9: "mil milion",
            1e12: "bilion",
            1e15: "mil bilion",
        }

        self.ords_2 = {1: "1r", 2: "2n", 3: "3r", 4: "4t"}
        self.ords_3 = {
            1: "unè",
            2: "dosè",
            3: "tresè",
            4: "quatrè",
            5: "cinquè",
            6: "sisè",
            7: "setè",
            8: "vuitè",
            9: "novè",
        }

    def merge(self, curr, next):
        ctext, cnum, ntext, nnum = curr + next
        if cnum == 1:
            if nnum < 1000000:
                return next
            ctext = "un"

        if nnum < cnum:
            if cnum < 100:
                return "%s-%s" % (ctext, ntext), cnum + nnum
            elif nnum == 1 or cnum == 100:
                return "%s %s" % (ctext, ntext), cnum + nnum
            else:
                return "%s %s" % (ctext, ntext), cnum + nnum
        elif (not nnum % 1000000) and cnum > 1:
            ntext = ntext[:-3] + "lions"
        if nnum == 100:
            ntext += "s"
            ctext += "-"
        else:
            ntext = " " + ntext
        return (ctext + ntext, cnum * nnum)

    def to_ordinal(self, value):
        self.verify_ordinal(value)
        if value == 0:
            text = ""
        elif value < 5:
            text = self.ords[value]
        elif value <= 20:
            text = "%s%s" % (self.ords[value], self.gender_stem)
        elif value <= 30:
            frac = value % 10
            text = "%s%s%s" % (self.ords[20], "-i-", self.ords_3[frac])
        elif value < 100:
            dec = (value // 10) * 10
            text = "%s%s%s%s" % (self.ords[dec], "a",
                                 "-", self.ords_3[value - dec])
        elif value == 1e2:
            text = "%s%s" % (self.ords[value], self.gender_stem)
        elif value < 2e2:
            cen = (value // 100) * 100
            text = "%s %s" % (self.ords[cen], self.to_ordinal(value - cen))
        elif value < 1e3:
            cen = (value // 100) * 100
            text = "%s%s %s" % (self.ords[cen], "s",
                                self.to_ordinal(value - cen))
        elif value == 1e3:
            text = "%s%s" % (self.ords[value], self.gender_stem)
        elif value < 1e6:
            dec = 1000 ** int(math.log(int(value), 1000))
            high_part, low_part = divmod(value, dec)
            cardinal = self.to_cardinal(high_part) if high_part != 1 else ""
            text = "%s %s %s" % (cardinal, self.ords[dec],
                                 self.to_ordinal(low_part))
        elif value < 1e18:
            dec = 1000 ** int(math.log(int(value), 1000))
            high_part, low_part = divmod(value, dec)
            cardinal = self.to_cardinal(high_part) if high_part != 1 else ""
            text = "%s%s%s %s" % (cardinal, self.ords[dec],
                                  self.gender_stem, self.to_ordinal(low_part))
        else:
            part1 = self.to_cardinal(value)
            text = "%s%s" % (part1[:-1], "onè")
        return text.strip()

    def to_ordinal_num(self, value):
        self.verify_ordinal(value)
        if value not in self.ords_2:
            return "%s%s" % (value, "è" if self.gender_stem == "è" else "a")
        else:
            return self.ords_2[value]

    def to_currency(self, val, currency="EUR", cents=True,
                    separator=" amb", adjective=False):
        result = super().to_currency(
            val, currency=currency, cents=cents,
            separator=separator, adjective=adjective
        )
        list_result = result.split(separator + " ")

        if currency in self.CURRENCIES_UNA:
            list_result[0] = list_result[0].replace("un", "una")
            list_result[0] = list_result[0].replace("dos", "dues")
            list_result[0] = list_result[0].replace("cents", "centes")

        list_result[0] = list_result[0].replace("vint-i-un", "vint-i-un")
        list_result[0] = list_result[0].replace(" i un", "-un")
        list_result[0] = list_result[0].replace("un", "un")

        if currency in self.CENTS_UNA:
            list_result[1] = list_result[1].replace("un", "una")
            list_result[1] = list_result[1].replace("dos", "dues")

        list_result[1] = list_result[1].replace("vint-i-un", "vint-i-una")

        list_result[1] = list_result[1].replace("un", "un")

        result = (separator + " ").join(list_result)

        return result


def patch_num2words():
    try:
        import num2words  # noqa: PLC0415
    except ImportError:
        _logger = logging.getLogger(__name__)
        _logger.warning("num2words is not available, Arabic number to words conversion will not work")
        return
    if MIN_PY_VERSION >= (3, 12):
        raise RuntimeError("The num2words monkey patch is obsolete. Bump the version of the library to the latest available in the official package repository, if it hasn't already been done, and remove the patch.")
    num2words.CONVERTER_CLASSES["ar"] = Num2Word_AR_Fixed()
    num2words.CONVERTER_CLASSES["bg"] = NumberToWords_BG()
    num2words.CONVERTER_CLASSES["ca"] = NumberToWords_CA()
