# -*- coding: utf-8 -*-
# Copyright (c) 2003, Taro Ogawa.  All Rights Reserved.
# Copyright (c) 2013, Savoir-faire Linux inc.  All Rights Reserved.
# Copyright (c) 2017, Tufan Kaynak, Framras.  All Rights Reserved.

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

from .base import Num2Word_Base


class Num2Word_TR(Num2Word_Base):
    def __init__(self):
        self.precision = 2
        self.negword = u"eksi"
        self.pointword = u"virgül"
        self.CURRENCY_UNIT = u"lira"
        self.CURRENCY_SUBUNIT = u"kuruş"
        self.errmsg_nonnum = u"Sadece sayılar yazıya çevrilebilir."
        self.errmsg_floatord = u"Tam sayı olmayan {} sıralamada kullanılamaz."
        self.errmsg_negord = u"Pozitif olmayan {} sıralamada kullanılamaz."
        self.errmsg_toobig = u"abs({}) sayı yazıya çevirmek için çok büyük. " \
                             u"Yazıya çevrilebilecek en büyük rakam {}."
        self.exclude_title = []
        self.DECIMAL_SIGN = ","
        self.ORDINAL_SIGN = "."
        self.ZERO = u"sıfır"
        self.CARDINAL_ONES = {
            "1": u"bir",
            "2": u"iki",
            "3": u"üç",
            "4": u"dört",
            "5": u"beş",
            "6": u"altı",
            "7": u"yedi",
            "8": u"sekiz",
            "9": u"dokuz"
        }
        self.ORDINAL_ONES = {
            "1": u"birinci",
            "2": u"ikinci",
            "3": u"üçüncü",
            "4": u"dördüncü",
            "5": u"beşinci",
            "6": u"altıncı",
            "7": u"yedinci",
            "8": u"sekizinci",
            "9": u"dokuzuncu"
        }
        self.CARDINAL_TENS = {
            "1": u"on",
            "2": u"yirmi",
            "3": u"otuz",
            "4": u"kırk",
            "5": u"elli",
            "6": u"altmış",
            "7": u"yetmiş",
            "8": u"seksen",
            "9": u"doksan"
        }
        self.ORDINAL_TENS = {
            "1": u"onuncu",
            "2": u"yirminci",
            "3": u"otuzuncu",
            "4": u"kırkıncı",
            "5": u"ellinci",
            "6": u"altmışıncı",
            "7": u"yetmişinci",
            "8": u"sekseninci",
            "9": u"doksanıncı"
        }
        self.HUNDREDS = {
            "2": u"iki",
            "3": u"üç",
            "4": u"dört",
            "5": u"beş",
            "6": u"altı",
            "7": u"yedi",
            "8": u"sekiz",
            "9": u"dokuz"
        }
        self.CARDINAL_HUNDRED = (u"yüz",)
        self.ORDINAL_HUNDRED = (u"yüzüncü",)
        self.CARDINAL_TRIPLETS = {
            1: u"bin",
            2: u"milyon",
            3: u"milyar",
            4: u"trilyon",
            5: u"katrilyon",
            6: u"kentilyon"
        }
        self.ORDINAL_TRIPLETS = {
            1: u"bininci",
            2: u"milyonuncu",
            3: u"milyarıncı",
            4: u"trilyonuncu",
            5: u"katrilyonuncu",
            6: u"kentilyon"
        }
        self.MAXVAL = (10 ** ((len(self.CARDINAL_TRIPLETS) + 1) * 3)) - 1

        self.integers_to_read = []
        self.total_triplets_to_read = 0
        self.total_digits_outside_triplets = 0
        self.order_of_last_zero_digit = 0

    def to_cardinal(self, value):
        wrd = ""
        is_cardinal = self.verify_cardinal(value)
        if not is_cardinal:
            return wrd

        if not int(value) == value:
            return self.to_cardinal_float(value)

        if str(value).startswith("-"):
            pre_word, value = self.negword, float(str(value)[1:])
        else:
            pre_word, value = "", float(value)

        self.to_splitnum(value)

        if self.order_of_last_zero_digit >= len(self.integers_to_read[0]):
            # number like 00 and all 0s and even more, raise error
            return "%s%s" % (pre_word, wrd)

        if self.total_triplets_to_read == 1:
            if self.total_digits_outside_triplets == 2:
                if self.order_of_last_zero_digit == 1:
                    # number like x0, read cardinal x0 and return
                    wrd += self.CARDINAL_TENS.get(
                        self.integers_to_read[0][0], ""
                    )
                    return "%s%s" % (pre_word, wrd)
                if self.order_of_last_zero_digit == 0:
                    # number like xy, read cardinal xy and return
                    wrd += self.CARDINAL_TENS.get(
                        self.integers_to_read[0][0], ""
                    )
                    wrd += self.CARDINAL_ONES.get(
                        self.integers_to_read[0][1], ""
                    )
                return "%s%s" % (pre_word, wrd)

            if self.total_digits_outside_triplets == 1:
                if self.order_of_last_zero_digit == 0:
                    # number like x, read cardinal x and return
                    wrd += self.CARDINAL_ONES.get(
                        self.integers_to_read[0][0], ""
                    )
                    if self.integers_to_read[0][0] == "0":
                        return self.ZERO
                    return "%s%s" % (pre_word, wrd)

            if self.total_digits_outside_triplets == 0:
                if self.order_of_last_zero_digit == 2:
                    # number like x00, read cardinal x00 and return
                    wrd += self.HUNDREDS.get(
                        self.integers_to_read[0][0], ""
                    )
                    wrd += self.CARDINAL_HUNDRED[0]
                    return "%s%s" % (pre_word, wrd)
                if self.order_of_last_zero_digit == 1:
                    # number like xy0, read cardinal xy0 and return
                    wrd += self.HUNDREDS.get(
                        self.integers_to_read[0][0], ""
                    )
                    wrd += self.CARDINAL_HUNDRED[0]
                    wrd += self.CARDINAL_TENS.get(
                        self.integers_to_read[0][1], ""
                    )
                    return "%s%s" % (pre_word, wrd)
                if self.order_of_last_zero_digit == 0:
                    # number like xyz, read cardinal xyz and return
                    wrd += self.HUNDREDS.get(
                        self.integers_to_read[0][0], ""
                    )
                    wrd += self.CARDINAL_HUNDRED[0]
                    wrd += self.CARDINAL_TENS.get(
                        self.integers_to_read[0][1], ""
                    )
                    wrd += self.CARDINAL_ONES.get(
                        self.integers_to_read[0][2], ""
                    )
                    return "%s%s" % (pre_word, wrd)

        if self.total_triplets_to_read >= 2:
            if self.total_digits_outside_triplets == 2:
                if self.order_of_last_zero_digit == len(
                        self.integers_to_read[0]) - 1:
                    # number like x0 and all 0s, read cardinal x0 0..0
                    #  and return
                    wrd += self.CARDINAL_TENS.get(
                        self.integers_to_read[0][0], ""
                    )
                    wrd += self.CARDINAL_TRIPLETS[
                        self.total_triplets_to_read - 1
                    ]
                    return "%s%s" % (pre_word, wrd)
                if self.order_of_last_zero_digit == len(
                        self.integers_to_read[0]) - 2:
                    # number like xy and all 0s, read cardinal xy 0..0
                    #  and return
                    wrd += self.CARDINAL_TENS.get(
                        self.integers_to_read[0][0], ""
                    )
                    wrd += self.CARDINAL_ONES.get(
                        self.integers_to_read[0][1], ""
                    )
                    wrd += self.CARDINAL_TRIPLETS[
                        self.total_triplets_to_read - 1
                    ]
                    return "%s%s" % (pre_word, wrd)
                if self.order_of_last_zero_digit < len(
                        self.integers_to_read[0]) - 2:
                    # number like xy and others, read cardinal xy n..n
                    #  and return
                    wrd += self.CARDINAL_TENS.get(
                        self.integers_to_read[0][0], ""
                    )
                    wrd += self.CARDINAL_ONES.get(
                        self.integers_to_read[0][1], ""
                    )
                    wrd += self.CARDINAL_TRIPLETS[
                        self.total_triplets_to_read - 1
                    ]

            if self.total_digits_outside_triplets == 1:
                if self.order_of_last_zero_digit == len(
                        self.integers_to_read[0]) - 1:
                    # number like x and all 0s, read cardinal x 0..0
                    #  and return
                    if not (self.total_triplets_to_read == 2 and
                            self.integers_to_read[0][0] == "1"):
                        wrd += self.CARDINAL_ONES.get(
                            self.integers_to_read[0][0], ""
                        )
                    wrd += self.CARDINAL_TRIPLETS[
                        self.total_triplets_to_read - 1
                    ]
                    return "%s%s" % (pre_word, wrd)
                if self.order_of_last_zero_digit < len(
                        self.integers_to_read[0]) - 1:
                    # number like x and others, read cardinal x n..n
                    #  and return
                    if not (self.total_triplets_to_read == 2 and
                            self.integers_to_read[0][0] == "1"):
                        wrd += self.CARDINAL_ONES.get(
                            self.integers_to_read[0][0], ""
                        )
                    wrd += self.CARDINAL_TRIPLETS[
                        self.total_triplets_to_read - 1
                    ]

            if self.total_digits_outside_triplets == 0:
                if self.order_of_last_zero_digit == len(
                        self.integers_to_read[0]) - 1:
                    # number like x00 and all 0s, read cardinal x00 0..0
                    #  and return
                    wrd += self.HUNDREDS.get(self.integers_to_read[0][0], "")
                    wrd += self.CARDINAL_HUNDRED[0]
                    wrd += self.CARDINAL_TRIPLETS[
                        self.total_triplets_to_read - 1
                    ]
                    return "%s%s" % (pre_word, wrd)
                if self.order_of_last_zero_digit == len(
                        self.integers_to_read[0]) - 2:
                    # number like xy0 and all 0s, read cardinal xy0 0..0
                    #  and return
                    wrd += self.HUNDREDS.get(
                        self.integers_to_read[0][0], ""
                    )
                    wrd += self.CARDINAL_HUNDRED[0]
                    wrd += self.CARDINAL_TENS.get(
                        self.integers_to_read[0][1], ""
                    )
                    wrd += self.CARDINAL_TRIPLETS[
                        self.total_triplets_to_read - 1
                    ]
                    return "%s%s" % (pre_word, wrd)
                if self.order_of_last_zero_digit == len(
                        self.integers_to_read[0]) - 3:
                    # number like xyz and all 0s, read cardinal xyz 0..0
                    #  and return
                    wrd += self.HUNDREDS.get(self.integers_to_read[0][0], "")
                    wrd += self.CARDINAL_HUNDRED[0]
                    wrd += self.CARDINAL_TENS.get(
                        self.integers_to_read[0][1], ""
                    )
                    wrd += self.CARDINAL_ONES.get(
                        self.integers_to_read[0][2], ""
                    )
                    wrd += self.CARDINAL_TRIPLETS[
                        self.total_triplets_to_read - 1
                    ]
                    return "%s%s" % (pre_word, wrd)
                if self.order_of_last_zero_digit < len(
                        self.integers_to_read[0]) - 3:
                    # number like xyz and all others, read cardinal xyz n..n
                    wrd += self.HUNDREDS.get(self.integers_to_read[0][0], "")
                    wrd += self.CARDINAL_HUNDRED[0]
                    wrd += self.CARDINAL_TENS.get(
                        self.integers_to_read[0][1], ""
                    )
                    if not (self.total_triplets_to_read == 2 and
                            self.integers_to_read[0][2] == "1"):
                        wrd += self.CARDINAL_ONES.get(
                            self.integers_to_read[0][2], ""
                        )
                    wrd += self.CARDINAL_TRIPLETS[
                        self.total_triplets_to_read - 1
                    ]

            for i in list(range(self.total_triplets_to_read - 1, 0, -1)):
                reading_triplet_order = self.total_triplets_to_read - i
                if self.total_digits_outside_triplets == 0:
                    last_read_digit_order = reading_triplet_order * 3
                else:
                    last_read_digit_order = (reading_triplet_order - 1) * 3 +\
                                            self.total_digits_outside_triplets

                if not self.integers_to_read[0][
                        last_read_digit_order: last_read_digit_order + 3
                ] == "000":
                    if not self.integers_to_read[0][
                        last_read_digit_order
                    ] == "0":
                        wrd += self.HUNDREDS.get(
                            self.integers_to_read[0][last_read_digit_order], ""
                        )
                        if self.order_of_last_zero_digit == len(
                                self.integers_to_read[0]) - (
                                last_read_digit_order) - 1:
                            if i == 1:
                                wrd += self.CARDINAL_HUNDRED[0]
                                return "%s%s" % (pre_word, wrd)
                            elif i > 1:
                                wrd += self.CARDINAL_HUNDRED[0]
                                wrd += self.CARDINAL_TRIPLETS[i - 1]
                                return "%s%s" % (pre_word, wrd)
                        else:
                            wrd += self.CARDINAL_HUNDRED[0]

                    if not self.integers_to_read[0][
                                last_read_digit_order + 1] == "0":
                        if self.order_of_last_zero_digit == len(
                                self.integers_to_read[0]) - (
                                last_read_digit_order) - 2:
                            if i == 1:
                                wrd += self.CARDINAL_TENS.get(
                                    self.integers_to_read[0][
                                        last_read_digit_order + 1], ""
                                )
                                return "%s%s" % (pre_word, wrd)
                            elif i > 1:
                                wrd += self.CARDINAL_TENS.get(
                                    self.integers_to_read[0][
                                        last_read_digit_order + 1], ""
                                )
                                wrd += self.CARDINAL_TRIPLETS[i - 1]
                                return "%s%s" % (pre_word, wrd)
                        else:
                            wrd += self.CARDINAL_TENS.get(
                                self.integers_to_read[0][
                                    last_read_digit_order + 1], ""
                            )

                    if not self.integers_to_read[0][
                                last_read_digit_order + 2] == "0":
                        if self.order_of_last_zero_digit == len(
                                self.integers_to_read[0]) - (
                                last_read_digit_order) - 3:
                            if i == 1:
                                wrd += self.CARDINAL_ONES.get(
                                    self.integers_to_read[0][
                                        last_read_digit_order + 2], ""
                                )
                                return "%s%s" % (pre_word, wrd)
                            if i == 2:
                                if not self.integers_to_read[0][
                                        last_read_digit_order:
                                        last_read_digit_order + 2
                                        ] == "00":
                                    wrd += self.CARDINAL_ONES.get(
                                        self.integers_to_read[0][
                                            last_read_digit_order + 2], ""
                                    )
                                elif not self.integers_to_read[0][
                                            last_read_digit_order + 2] == "1":
                                    wrd += self.CARDINAL_ONES.get(
                                        self.integers_to_read[0][
                                            last_read_digit_order + 2], ""
                                    )
                                wrd += self.CARDINAL_TRIPLETS[i - 1]
                                return "%s%s" % (pre_word, wrd)
                            if i > 2:
                                wrd += self.CARDINAL_ONES.get(
                                    self.integers_to_read[0][
                                        last_read_digit_order + 2], ""
                                )
                                wrd += self.CARDINAL_TRIPLETS[i - 1]
                                return "%s%s" % (pre_word, wrd)
                        else:
                            if not self.integers_to_read[0][
                                    last_read_digit_order:
                                    last_read_digit_order + 2
                            ] == "00":
                                wrd += self.CARDINAL_ONES.get(
                                    self.integers_to_read[0][
                                        last_read_digit_order + 2], ""
                                )
                            else:
                                if i == 2:
                                    if not self.integers_to_read[0][
                                           last_read_digit_order:
                                           last_read_digit_order + 2
                                    ] == "00":
                                        wrd += self.CARDINAL_ONES.get(
                                            self.integers_to_read[0][
                                                last_read_digit_order + 2], ""
                                        )
                                    elif not self.integers_to_read[0][
                                                last_read_digit_order + 2
                                    ] == "1":
                                        wrd += self.CARDINAL_ONES.get(
                                            self.integers_to_read[0][
                                                last_read_digit_order + 2], ""
                                        )

                    wrd += self.CARDINAL_TRIPLETS[i - 1]

        return "%s%s" % (pre_word, wrd)

    def to_cardinal_float(self, value):
        self.to_splitnum(value)
        wrd = ""
        wrd += self.pointword
        if len(self.integers_to_read[1]) >= 1:
            wrd += self.CARDINAL_TENS.get(self.integers_to_read[1][0], "")

        if len(self.integers_to_read[1]) == 2:
            wrd += self.CARDINAL_ONES.get(self.integers_to_read[1][1], "")

        if self.integers_to_read[0] == "0":
            wrd = self.ZERO + wrd
        else:
            wrd = self.to_cardinal(int(self.integers_to_read[0])) + wrd
        return wrd

    def verify_cardinal(self, value):
        iscardinal = True
        try:
            if not float(value) == value:
                iscardinal = False
        except (ValueError, TypeError):
            raise TypeError(self.errmsg_nonnum)
        if abs(value) >= self.MAXVAL:
            raise OverflowError(self.errmsg_toobig.format(value, self.MAXVAL))
        return iscardinal

    def verify_ordinal(self, value):
        isordinal = True
        try:
            if not int(value) == value:
                isordinal = False
            if not abs(value) == value:
                raise TypeError(self.errmsg_negord.format(value))
        except (ValueError, TypeError):
            raise TypeError(self.errmsg_nonnum)
        if abs(value) >= self.MAXVAL:
            raise OverflowError(self.errmsg_toobig.format(value, self.MAXVAL))
        return isordinal

    def to_ordinal(self, value):
        wrd = ""
        isordinal = self.verify_ordinal(value)
        if isordinal:
            self.to_splitnum(value)

            if self.order_of_last_zero_digit >= len(self.integers_to_read[0]):
                # number like 00 and all 0s and even more, raise error
                return wrd

            if self.total_triplets_to_read == 1:
                if self.total_digits_outside_triplets == 2:
                    if self.order_of_last_zero_digit == 1:
                        # number like x0, read ordinal x0 and return
                        wrd += self.ORDINAL_TENS.get(
                            self.integers_to_read[0][0], ""
                        )
                        return wrd
                    if self.order_of_last_zero_digit == 0:
                        # number like xy, read ordinal xy and return
                        wrd += self.CARDINAL_TENS.get(
                            self.integers_to_read[0][0], ""
                        )
                        wrd += self.ORDINAL_ONES.get(
                            self.integers_to_read[0][1], ""
                        )
                        return wrd

                if self.total_digits_outside_triplets == 1:
                    if self.order_of_last_zero_digit == 0:
                        # number like x, read ordinal x and return
                        wrd += self.ORDINAL_ONES.get(
                            self.integers_to_read[0][0], ""
                        )
                        if self.integers_to_read[0][0] == "0":
                            return u"sıfırıncı"
                        return wrd

                if self.total_digits_outside_triplets == 0:
                    if self.order_of_last_zero_digit == 2:
                        # number like x00, read ordinal x00 and return
                        wrd += self.HUNDREDS.get(
                            self.integers_to_read[0][0], ""
                        )
                        wrd += self.ORDINAL_HUNDRED[0]
                        return wrd
                    if self.order_of_last_zero_digit == 1:
                        # number like xy0, read ordinal xy0 and return
                        wrd += self.HUNDREDS.get(
                            self.integers_to_read[0][0], ""
                        )
                        wrd += self.CARDINAL_HUNDRED[0]
                        wrd += self.ORDINAL_TENS.get(
                            self.integers_to_read[0][1], ""
                        )
                        return wrd
                    if self.order_of_last_zero_digit == 0:
                        # number like xyz, read ordinal xyz and return
                        wrd += self.HUNDREDS.get(
                            self.integers_to_read[0][0], ""
                        )
                        wrd += self.CARDINAL_HUNDRED[0]
                        wrd += self.CARDINAL_TENS.get(
                            self.integers_to_read[0][1], ""
                        )
                        if not self.integers_to_read[0][2] == "0":
                            wrd += self.ORDINAL_ONES.get(
                                self.integers_to_read[0][2], ""
                            )
                        return wrd

            if self.total_triplets_to_read >= 2:
                if self.total_digits_outside_triplets == 2:
                    if self.order_of_last_zero_digit == len(
                            self.integers_to_read[0]) - 1:
                        # number like x0 and all 0s, read ordinal x0 0..0
                        #  and return
                        wrd += self.CARDINAL_TENS.get(
                            self.integers_to_read[0][0], ""
                        )
                        wrd += self.ORDINAL_TRIPLETS[
                            self.total_triplets_to_read - 1
                        ]
                        return wrd
                    if self.order_of_last_zero_digit == len(
                            self.integers_to_read[0]) - 2:
                        # number like xy and all 0s, read ordinal xy 0..0
                        #  and return
                        wrd += self.CARDINAL_TENS.get(
                            self.integers_to_read[0][0], ""
                        )
                        wrd += self.CARDINAL_ONES.get(
                            self.integers_to_read[0][1], ""
                        )
                        wrd += self.ORDINAL_TRIPLETS[
                            self.total_triplets_to_read - 1
                        ]
                        return wrd
                    if self.order_of_last_zero_digit < len(
                            self.integers_to_read[0]) - 2:
                        # number like xy and others, read cardinal xy n..n
                        #  and return
                        wrd += self.CARDINAL_TENS.get(
                            self.integers_to_read[0][0], ""
                        )
                        wrd += self.CARDINAL_ONES.get(
                            self.integers_to_read[0][1], ""
                        )
                        wrd += self.CARDINAL_TRIPLETS[
                            self.total_triplets_to_read - 1
                        ]

                if self.total_digits_outside_triplets == 1:
                    if self.order_of_last_zero_digit == len(
                            self.integers_to_read[0]) - 1:
                        # number like x and all 0s, read ordinal x 0..0
                        #  and return
                        if not (self.total_triplets_to_read == 2 and
                                self.integers_to_read[0][0] == "1"):
                            wrd += self.CARDINAL_ONES.get(
                                self.integers_to_read[0][0], ""
                            )
                        wrd += self.ORDINAL_TRIPLETS[
                            self.total_triplets_to_read - 1
                        ]
                        return wrd
                    if self.order_of_last_zero_digit < len(
                            self.integers_to_read[0]) - 1:
                        # number like x and others, read cardinal x n..n
                        #  and return
                        if not (self.total_triplets_to_read == 2 and
                                self.integers_to_read[0][0] == "1"):
                            wrd += self.CARDINAL_ONES.get(
                                self.integers_to_read[0][0], ""
                            )
                        wrd += self.CARDINAL_TRIPLETS[
                            self.total_triplets_to_read - 1
                        ]

                if self.total_digits_outside_triplets == 0:
                    if self.order_of_last_zero_digit == len(
                            self.integers_to_read[0]) - 1:
                        # number like x00 and all 0s, read ordinal x00 0..0
                        #  and return
                        wrd += self.HUNDREDS.get(
                            self.integers_to_read[0][0], ""
                        )
                        wrd += self.CARDINAL_HUNDRED[0]
                        wrd += self.ORDINAL_TRIPLETS[
                            self.total_triplets_to_read - 1
                        ]
                        return wrd
                    if self.order_of_last_zero_digit == len(
                            self.integers_to_read[0]) - 2:
                        # number like xy0 and all 0s, read ordinal xy0 0..0
                        #  and return
                        wrd += self.HUNDREDS.get(
                            self.integers_to_read[0][0], ""
                        )
                        wrd += self.CARDINAL_HUNDRED[0]
                        wrd += self.CARDINAL_TENS.get(
                            self.integers_to_read[0][1], ""
                        )
                        wrd += self.ORDINAL_TRIPLETS[
                            self.total_triplets_to_read - 1
                        ]
                        return wrd
                    if self.order_of_last_zero_digit == len(
                            self.integers_to_read[0]) - 3:
                        # number like xyz and all 0s, read ordinal xyz 0..0
                        #  and return
                        wrd += self.HUNDREDS.get(
                            self.integers_to_read[0][0], ""
                        )
                        wrd += self.CARDINAL_HUNDRED[0]
                        wrd += self.CARDINAL_TENS.get(
                            self.integers_to_read[0][1], ""
                        )
                        wrd += self.CARDINAL_ONES.get(
                            self.integers_to_read[0][2], ""
                        )
                        wrd += self.ORDINAL_TRIPLETS[
                            self.total_triplets_to_read - 1
                        ]
                        return wrd
                    if self.order_of_last_zero_digit < len(
                            self.integers_to_read[0]) - 3:
                        # number like xyz and all others, read cardinal
                        #  xyz n..n
                        wrd += self.HUNDREDS.get(
                            self.integers_to_read[0][0], ""
                        )
                        wrd += self.CARDINAL_HUNDRED[0]
                        wrd += self.CARDINAL_TENS.get(
                            self.integers_to_read[0][1], ""
                        )
                        if not (self.total_triplets_to_read == 2 and
                                self.integers_to_read[0][2] == "1"):
                            wrd += self.CARDINAL_ONES.get(
                                self.integers_to_read[0][2], ""
                            )
                        wrd += self.CARDINAL_TRIPLETS[
                            self.total_triplets_to_read - 1
                        ]

                for i in list(range(self.total_triplets_to_read - 1, 0, -1)):
                    reading_triplet_order = self.total_triplets_to_read - i
                    if self.total_digits_outside_triplets == 0:
                        last_read_digit_order = reading_triplet_order * 3
                    else:
                        last_read_digit_order = \
                            (reading_triplet_order - 1) * 3 + \
                            self.total_digits_outside_triplets

                    if not self.integers_to_read[0][
                           last_read_digit_order: last_read_digit_order + 3
                           ] == "000":
                        if not self.integers_to_read[0][
                            last_read_digit_order
                        ] == "0":
                            if not self.integers_to_read[0][
                                last_read_digit_order
                            ] == "1":
                                wrd += self.CARDINAL_ONES.get(
                                    self.integers_to_read[0][
                                        last_read_digit_order
                                    ], ""
                                )
                            if self.order_of_last_zero_digit == len(
                                    self.integers_to_read[0]) - (
                                    last_read_digit_order) - 1:
                                if i == 1:
                                    wrd += self.ORDINAL_HUNDRED[0]
                                    return wrd
                                elif i > 1:
                                    wrd += self.CARDINAL_HUNDRED[0]
                                    wrd += self.ORDINAL_TRIPLETS[i - 1]
                                    return wrd
                            else:
                                wrd += self.CARDINAL_HUNDRED[0]

                        if not self.integers_to_read[0][
                                    last_read_digit_order + 1
                        ] == "0":
                            if self.order_of_last_zero_digit == len(
                                    self.integers_to_read[0]) - (
                                    last_read_digit_order) - 2:
                                if i == 1:
                                    wrd += self.ORDINAL_TENS.get(
                                        self.integers_to_read[0][
                                            last_read_digit_order + 1], ""
                                    )
                                    return wrd
                                elif i > 1:
                                    wrd += self.CARDINAL_TENS.get(
                                        self.integers_to_read[0][
                                            last_read_digit_order + 1], ""
                                    )
                                    wrd += self.ORDINAL_TRIPLETS[i - 1]
                                    return wrd
                            else:
                                wrd += self.CARDINAL_TENS.get(
                                    self.integers_to_read[0][
                                        last_read_digit_order + 1], ""
                                )

                        if not self.integers_to_read[0][
                                    last_read_digit_order + 2
                        ] == "0":
                            if self.order_of_last_zero_digit == len(
                                    self.integers_to_read[0]) - (
                                    last_read_digit_order) - 3:
                                if i == 1:
                                    wrd += self.ORDINAL_ONES.get(
                                        self.integers_to_read[0][
                                            last_read_digit_order + 2], ""
                                    )
                                    return wrd
                                if i == 2:
                                    if not self.integers_to_read[0][
                                       last_read_digit_order:
                                            last_read_digit_order + 2] == "00":
                                        wrd += self.CARDINAL_ONES.get(
                                            self.integers_to_read[0][
                                                last_read_digit_order + 2], ""
                                        )
                                    elif not self.integers_to_read[0][
                                                last_read_digit_order + 2
                                    ] == "1":
                                        wrd += self.CARDINAL_ONES.get(
                                            self.integers_to_read[0][
                                                last_read_digit_order + 2], ""
                                        )
                                    wrd += self.ORDINAL_TRIPLETS[i - 1]
                                    return wrd
                                if i > 2:
                                    wrd += self.CARDINAL_ONES.get(
                                        self.integers_to_read[0][
                                            last_read_digit_order + 2], ""
                                    )
                                    wrd += self.ORDINAL_TRIPLETS[i - 1]
                                    return wrd
                            else:
                                if not self.integers_to_read[0][
                                   last_read_digit_order:
                                        last_read_digit_order + 2] == "00":
                                    wrd += self.CARDINAL_ONES.get(
                                        self.integers_to_read[0][
                                            last_read_digit_order + 2], ""
                                    )
                                else:
                                    if not self.integers_to_read[0][
                                       last_read_digit_order:
                                           last_read_digit_order + 2] == "00":
                                        wrd += self.CARDINAL_ONES.get(
                                            self.integers_to_read[0][
                                                last_read_digit_order + 2], ""
                                        )
                                    elif not self.integers_to_read[0][
                                            last_read_digit_order + 2] == "1":
                                        wrd += self.CARDINAL_ONES.get(
                                            self.integers_to_read[0][
                                                last_read_digit_order + 2], ""
                                        )

                        wrd += self.CARDINAL_TRIPLETS[i - 1]

        return wrd

    def to_ordinal_num(self, value):
        self.verify_ordinal(value)
        return "%s%s" % (value, self.to_ordinal(value)[-4:])

    def to_splitnum(self, val):
        float_digits = str(int(val * 10 ** self.precision))
        if not int(val) == 0:
            self.integers_to_read = [
                str(int(val)),
                float_digits[len(float_digits) - self.precision:]
            ]
        else:
            self.integers_to_read = [
                "0",
                "0" * (self.precision - len(float_digits)) +
                float_digits[len(float_digits) - self.precision:]
            ]
        if len(self.integers_to_read[0]) % 3 > 0:
            self.total_triplets_to_read = (len(self.integers_to_read[0]) // 3)\
                                          + 1
        elif len(self.integers_to_read[0]) % 3 == 0:
            self.total_triplets_to_read = len(self.integers_to_read[0]) // 3
        self.total_digits_outside_triplets = len(self.integers_to_read[0]) % 3

        okunacak = list(self.integers_to_read[0][::-1])
        self.order_of_last_zero_digit = 0
        found = 0
        for i in range(len(okunacak) - 1):
            if int(okunacak[i]) == 0 and found == 0:
                self.order_of_last_zero_digit = i + 1
            else:
                found = 1

    def to_currency(self, value):
        if int(value) == 0:
            return u"bedelsiz"
        valueparts = self.to_cardinal(value).split(self.pointword)
        if len(valueparts) == 1:
            return valueparts[0] + self.CURRENCY_UNIT
        if len(valueparts) == 2:
            return self.CURRENCY_UNIT.join(valueparts) + \
                   self.CURRENCY_SUBUNIT
