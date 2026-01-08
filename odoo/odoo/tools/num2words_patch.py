import decimal
import math
import re
from collections import OrderedDict
from decimal import ROUND_HALF_UP, Decimal
from math import floor

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
