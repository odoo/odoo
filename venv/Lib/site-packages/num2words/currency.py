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

from __future__ import division

from decimal import ROUND_HALF_UP, Decimal


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
