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

from .base import Num2Word_Base
from .compat import to_s
from .currency import parse_currency_parts
from .utils import get_digits, splitbyx

ZERO = (u'אפס',)

ONES = {
    1: (u'אחת', u'אחד', u'אחת', u'אחד',
        u'ראשונה', u'ראשון', u'ראשונות', u'ראשונים'),
    2: (u'שתיים', u'שניים', u'שתי', u'שני',
        u'שנייה', u'שני', u'שניות', u'שניים'),
    3: (u'שלוש', u'שלושה', u'שלוש', u'שלושת',
        u'שלישית', u'שלישי', u'שלישיות', u'שלישיים'),
    4: (u'ארבע', u'ארבעה', u'ארבע', u'ארבעת',
        u'רביעית', u'רביעי', u'רביעיות', u'רביעיים'),
    5: (u'חמש', u'חמישה', u'חמש', u'חמשת',
        u'חמישית', u'חמישי', u'חמישיות', u'חמישיים'),
    6: (u'שש', u'שישה', u'שש', u'ששת',
        u'שישית', u'שישי', u'שישיות', u'שישיים'),
    7: (u'שבע', u'שבעה', u'שבע', u'שבעת',
        u'שביעית', u'שביעי', u'שביעיות', u'שביעיים'),
    8: (u'שמונה', u'שמונה', u'שמונה', u'שמונת',
        u'שמינית', u'שמיני', u'שמיניות', u'שמיניים'),
    9: (u'תשע', u'תשעה', u'תשע', u'תשעת',
        u'תשיעית', u'תשיעי', u'תשיעיות', u'תשיעיים'),
}

TENS = {
    0: (u'עשר', u'עשרה', u'עשר', u'עשרת',
        u'עשירית', u'עשירי', u'עשיריות', u'עשיריים'),
    1: (u'עשרה', u'עשר'),
    2: (u'שתים עשרה', u'שנים עשר'),
}

TWENTIES = {
    2: (u'עשרים',),
    3: (u'שלושים',),
    4: (u'ארבעים',),
    5: (u'חמישים',),
    6: (u'שישים',),
    7: (u'שבעים',),
    8: (u'שמונים',),
    9: (u'תשעים',),
}

HUNDREDS = {
    1: (u'מאה', u'מאת'),
    2: (u'מאתיים',),
    3: (u'מאות',)
}

THOUSANDS = {
    1: (u'אלף',),
    2: (u'אלפיים',),
    3: (u'אלפים', 'אלפי'),
}

LARGE = {
    1: (u'מיליון', u'מיליוני'),
    2: (u'מיליארד', u'מיליארדי'),
    3: (u'טריליון', u'טריליוני'),
    4: (u'קוודריליון', u'קוודריליוני'),
    5: (u'קווינטיליון', u'קווינטיליוני'),
    6: (u'סקסטיליון', u'סקסטיליוני'),
    7: (u'ספטיליון', u'ספטיליוני'),
    8: (u'אוקטיליון', u'אוקטיליוני'),
    9: (u'נוניליון', u'נוניליוני'),
    10: (u'דסיליון', u'דסיליוני'),
    11: (u'אונדסיליון', u'אונדסיליוני'),
    12: (u'דואודסיליון', u'דואודסיליוני'),
    13: (u'טרדסיליון', u'טרדסיליוני'),
    14: (u'קווטואורדסיליון', u'קווטואורדסיליוני'),
    15: (u'קווינדסיליון', u'קווינדסיליוני'),
    16: (u'סקסדסיליון', u'סקסדסיליוני'),
    17: (u'ספטנדסיליון', u'ספטנדסיליוני'),
    18: (u'אוקטודסיליון', u'אוקטודסיליוני'),
    19: (u'נובמדסיליון', u'נובמדסיליוני'),
    20: (u'ויגינטיליון', u'ויגינטיליוני')
}

AND = u'ו'

DEF = u'ה'

MAXVAL = int('1' + '0'*66)


def chunk2word(n, i, x, gender='f', construct=False,
               ordinal=False, plural=False):
    words = []
    n1, n2, n3 = get_digits(x)

    if n3 > 0:
        if construct and n == 100:
            words.append(HUNDREDS[n3][1])
        elif n3 <= 2:
            words.append(HUNDREDS[n3][0])
        else:
            words.append(ONES[n3][0] + ' ' + HUNDREDS[3][0])

    if n2 > 1:
        words.append(TWENTIES[n2][0])

    if i == 0 or x >= 11:
        male = gender == 'm' or i > 0
        cop = (2*(construct and i == 0)+4*ordinal+2*plural) * (n < 11)
        if n2 == 1:
            if n1 == 0:
                words.append(TENS[n1][male + cop])
            elif n1 == 2:
                words.append(TENS[n1][male])
            else:
                words.append(ONES[n1][male] + ' ' + TENS[1][male])
        elif n1 > 0:
            words.append(ONES[n1][male + cop])

    construct_last = construct and (n % 1000 ** i == 0)

    if i == 1:
        if x >= 11:
            words[-1] = words[-1] + ' ' + THOUSANDS[1][0]
        elif n1 == 0:
            words.append(TENS[0][3] + ' ' + THOUSANDS[3][construct_last])
        elif n1 <= 2:
            words.append(THOUSANDS[n1][0])
        else:
            words.append(ONES[n1][3] + ' ' + THOUSANDS[3][construct_last])

    elif i > 1:
        if x >= 11:
            words[-1] = words[-1] + ' ' + LARGE[i - 1][construct_last]
        elif n1 == 0:
            words.append(TENS[0][1 + 2*construct_last] + ' ' +
                         LARGE[i - 1][construct_last])
        elif n1 == 1:
            words.append(LARGE[i - 1][0])
        else:
            words.append(ONES[n1][1 + 2*(construct_last or x == 2)] + ' ' +
                         LARGE[i - 1][construct_last])

    return words


def int2word(n, gender='f', construct=False,
             ordinal=False, definite=False, plural=False):
    assert n == int(n)
    assert not construct or not ordinal
    assert ordinal or (not definite and not plural)
    if n >= MAXVAL:
        raise OverflowError('abs(%s) must be less than %s.' % (n, MAXVAL))

    if n == 0:
        if ordinal:
            return DEF + ZERO[0]
        return ZERO[0]

    words = []

    chunks = list(splitbyx(str(n), 3))
    i = len(chunks)
    for x in chunks:
        i -= 1

        if x == 0:
            continue

        words += chunk2word(n, i, x, gender=gender, construct=construct,
                            ordinal=ordinal, plural=plural)

        # https://hebrew-academy.org.il/2017/01/30/%D7%95-%D7%94%D7%97%D7%99%D7%91%D7%95%D7%A8-%D7%91%D7%9E%D7%A1%D7%A4%D7%A8%D7%99%D7%9D  # noqa
        if len(words) > 1:
            words[-1] = AND + words[-1]

    if ordinal and (n >= 11 or definite):
        words[0] = DEF + words[0]

    return ' '.join(words)


class Num2Word_HE(Num2Word_Base):
    CURRENCY_FORMS = {
        'ILS': ((u'שקל', u'שקלים'), (u'אגורה', u'אגורות')),
        'EUR': ((u'אירו', u'אירו'), (u'סנט', u'סנטים')),
        'USD': ((u'דולר', u'דולרים'), (u'סנט', u'סנטים')),
    }

    CURRENCY_GENDERS = {
        'ILS': ('m', 'f'),
        'EUR': ('m', 'm'),
        'USD': ('m', 'm'),
    }

    def __init__(self, makaf='-'):
        super(Num2Word_HE, self).__init__()
        self.makaf = makaf

    def setup(self):
        super(Num2Word_HE, self).setup()
        self.negword = u'מינוס'
        self.pointword = u'נקודה'
        self.MAXVAL = MAXVAL

    def to_cardinal_float(self, value, gender='f'):
        try:
            float(value) == value
        except (ValueError, TypeError, AssertionError, AttributeError):
            raise TypeError(self.errmsg_nonnum % value)

        pre, post = self.float2tuple(float(value))

        post = str(post)
        post = '0'*(self.precision - len(post)) + post

        out = [self.to_cardinal(pre, gender=gender)]
        if self.precision:
            out.append(self.title(self.pointword))

        for i in range(self.precision):
            curr = int(post[i])
            out.append(to_s(self.to_cardinal(curr)))

        return ' '.join(out)

    def to_cardinal(self, value, gender='f', construct=False):
        try:
            assert int(value) == value
        except (ValueError, TypeError, AssertionError):
            # https://hebrew-academy.org.il/2019/12/03/%D7%A2%D7%9C-%D7%94%D7%91%D7%A2%D7%AA-%D7%94%D7%9E%D7%A1%D7%A4%D7%A8-%D7%94%D7%9E%D7%A2%D7%95%D7%A8%D7%91  # noqa
            return self.to_cardinal_float(value, gender=gender)

        out = ""
        if value < 0:
            value = abs(value)
            out = "%s " % self.negword.strip()

        if value >= self.MAXVAL:
            raise OverflowError(self.errmsg_toobig % (value, self.MAXVAL))

        return out + int2word(int(value), gender=gender, construct=construct)

    def to_ordinal(self, value, gender='m', definite=False, plural=False):
        self.verify_ordinal(value)

        if value >= self.MAXVAL:
            raise OverflowError(self.errmsg_toobig % (value, self.MAXVAL))

        return int2word(int(value), gender=gender, ordinal=True,
                        definite=definite, plural=plural)

    def pluralize(self, n, forms, currency=None, prefer_singular=False):
        assert n == int(n)
        form = 1
        if n == 1 or prefer_singular and (
                abs(n) >= 11 or n == 0 or currency != 'ILS'):
            form = 0
        return forms[form]

    def to_currency(self, val, currency='ILS', cents=True,
                    separator=AND, adjective=False,
                    prefer_singular=False, prefer_singular_cents=False):
        left, right, is_negative = parse_currency_parts(val)

        if not separator.startswith(' '):
            separator = ' ' + separator

        try:
            cr1, cr2 = self.CURRENCY_FORMS[currency]

        except KeyError:
            raise NotImplementedError(
                'Currency code "%s" not implemented for "%s"' %
                (currency, self.__class__.__name__))

        minus_str = "%s " % self.negword.strip() if is_negative else ""
        try:
            gender1, gender2 = self.CURRENCY_GENDERS[currency]
        except KeyError:
            gender1 = gender2 = ''

        money_str = self.to_cardinal(left, gender=gender1,
                                     construct=left == 2)
        if cents:
            cents_str = self.to_cardinal(right, gender=gender2,
                                         construct=right == 2)
        else:
            cents_str = self._cents_terse(right, currency)
            sep_parts = separator.split()
            if sep_parts and sep_parts[-1] == AND:
                separator += self.makaf

        strings = [
            minus_str,
            money_str,
            self.pluralize(left, cr1, currency=currency,
                           prefer_singular=prefer_singular),
            separator,
            cents_str,
            self.pluralize(right, cr2, currency=currency,
                           prefer_singular=prefer_singular_cents)
        ]
        if left == 1:
            strings[1], strings[2] = strings[2], strings[1]
        if right == 1:
            strings[4], strings[5] = strings[5], strings[4]
        # In Hebrew the separator is along with the following word
        return u'%s%s %s%s%s %s' % tuple(strings)
