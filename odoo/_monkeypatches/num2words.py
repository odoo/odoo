import math
from collections import OrderedDict
from decimal import ROUND_HALF_UP, Decimal

# The following section of the code is used to add support for the Bulgarian language in the num2words package.
# Part of the code is taken from num2words package: https://github.com/savoirfairelinux/num2words


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
            post = round(post)
        else:
            post = math.floor(post)

        return pre, post

    def to_cardinal_float(self, value):
        try:
            _ = float(value) == value
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

            power = sizeof_num_groups - i

            if num_groups[i] != '000':
                if int(num_groups[i]) > 1:
                    if power == 1:
                        ret[j] += self._show_digits_group(num_groups[i], 0, not self._last_and and i) + self._sep
                        ret[j] += self._exponent[(power - 1) * 3]
                    elif power == 2:
                        ret[j] += self._show_digits_group(num_groups[i], -1, not self._last_and and i) + self._sep
                        ret[j] += self._misc_strings['hiliadi'] + self._sep
                    else:
                        ret[j] += self._show_digits_group(num_groups[i], 1, not self._last_and and i) + self._sep
                        ret[j] += self._exponent[(power - 1) * 3] + self._plural + self._sep
                else:
                    if power == 1:
                        ret[j] += self._show_digits_group(num_groups[i], 0, not self._last_and and i) + self._sep
                    elif power == 2:
                        ret[j] += self._exponent[(power - 1) * 3] + self._sep
                    else:
                        ret[j] += self._digits[1][1] + self._sep + self._exponent[(power - 1) * 3] + self._sep

            i -= 1
            j += 1

        ret = self._discard_empties(ret)
        ret.reverse()
        return ret_minus + ''.join(ret)


def patch_module():
    try:
        import num2words  # noqa: PLC0415
    except ImportError:
        return
    num2words.CONVERTER_CLASSES['bg'] = NumberToWords_BG()
