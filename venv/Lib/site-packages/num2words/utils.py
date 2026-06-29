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


def splitbyx(n, x, format_int=True):
    length = len(n)
    if length > x:
        start = length % x
        if start > 0:
            result = n[:start]
            yield int(result) if format_int else result
        for i in range(start, length, x):
            result = n[i:i+x]
            yield int(result) if format_int else result
    else:
        yield int(n) if format_int else n


def get_digits(n):
    a = [int(x) for x in reversed(list(('%03d' % n)[-3:]))]
    return a
