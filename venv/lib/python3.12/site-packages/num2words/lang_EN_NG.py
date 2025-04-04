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

from __future__ import unicode_literals

from . import lang_EN


class Num2Word_EN_NG(lang_EN.Num2Word_EN):

    CURRENCY_FORMS = {'NGN': (('naira', 'naira'), ('kobo', 'kobo'))}

    CURRENCY_ADJECTIVES = {'NGN': 'Nigerian'}

    def to_currency(
        self, val, currency='NGN',
        kobo=True, separator=',',
        adjective=False
    ):
        result = super(Num2Word_EN_NG, self).to_currency(
            val, currency=currency, cents=kobo, separator=separator,
            adjective=adjective)
        return result
