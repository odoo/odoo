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

from .utils import get_digits, splitbyx

ZERO = (u'אפס',)

ONES = {
    1: (u'אחד',),
    2: (u'שנים',),
    3: (u'שלש',),
    4: (u'ארבע',),
    5: (u'חמש',),
    6: (u'שש',),
    7: (u'שבע',),
    8: (u'שמנה',),
    9: (u'תשע',),
}

TENS = {
    0: (u'עשר',),
    1: (u'אחד עשרה',),
    2: (u'שנים עשרה',),
    3: (u'שלש עשרה',),
    4: (u'ארבע עשרה',),
    5: (u'חמש עשרה',),
    6: (u'שש עשרה',),
    7: (u'שבע עשרה',),
    8: (u'שמנה עשרה',),
    9: (u'תשע עשרה',),
}

TWENTIES = {
    2: (u'עשרים',),
    3: (u'שלשים',),
    4: (u'ארבעים',),
    5: (u'חמישים',),
    6: (u'ששים',),
    7: (u'שבעים',),
    8: (u'שמנים',),
    9: (u'תשעים',),
}

HUNDRED = {
    1: (u'מאה',),
    2: (u'מאתיים',),
    3: (u'מאות',)
}

THOUSANDS = {
    1: (u'אלף',),
    2: (u'אלפיים',),
}

AND = u'ו'


def pluralize(n, forms):
    # gettext implementation:
    # (n%10==1 && n%100!=11 ? 0 : n != 0 ? 1 : 2)

    form = 0 if (n % 10 == 1 and n % 100 != 11) else 1 if n != 0 else 2

    return forms[form]


def int2word(n):
    if n > 9999:  # doesn't yet work for numbers this big
        raise NotImplementedError()

    if n == 0:
        return ZERO[0]

    words = []

    chunks = list(splitbyx(str(n), 3))
    i = len(chunks)
    for x in chunks:
        i -= 1

        if x == 0:
            continue

        n1, n2, n3 = get_digits(x)

        if n3 > 0:
            if n3 <= 2:
                words.append(HUNDRED[n3][0])
            else:
                words.append(ONES[n3][0])
                words.append(HUNDRED[3][0])

        if n2 > 1:
            words.append(TWENTIES[n2][0])

        if n2 == 1:
            words.append(TENS[n1][0])
        elif n1 > 0 and not (i > 0 and x == 1):
            words.append(ONES[n1][0])

        if i > 0:
            if i <= 2:
                words.append(THOUSANDS[i][0])
            else:
                words.append(ONES[i][0])
                words.append(THOUSANDS[1][0])

    if len(words) > 1:
        words[-1] = AND + words[-1]
    return ' '.join(words)


def n2w(n):
    return int2word(int(n))


def to_currency(n, currency='EUR', cents=True, seperator=','):
    raise NotImplementedError()


class Num2Word_HE(object):
    def to_cardinal(self, number):
        return n2w(number)

    def to_ordinal(self, number):
        raise NotImplementedError()


if __name__ == '__main__':
    yo = Num2Word_HE()
    nums = [1, 11, 21, 24, 99, 100, 101, 200, 211, 345, 1000, 1011]
    for num in nums:
        print(num, yo.to_cardinal(num))
