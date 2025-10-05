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


class Num2Word_ID():
    BASE = {0: [],
            1: ["satu"],
            2: ["dua"],
            3: ["tiga"],
            4: ["empat"],
            5: ["lima"],
            6: ["enam"],
            7: ["tujuh"],
            8: ["delapan"],
            9: ["sembilan"]}

    TENS_TO = {3: "ribu",
               6: "juta",
               9: "miliar",
               12: "triliun",
               15: "kuadriliun",
               18: "kuantiliun",
               21: "sekstiliun",
               24: "septiliun",
               27: "oktiliun",
               30: "noniliun",
               33: "desiliun"}

    errmsg_floatord = "Cannot treat float number as ordinal"
    errmsg_negord = "Cannot treat negative number as ordinal"
    errmsg_toobig = "Too large"
    max_num = 10 ** 36

    def split_by_koma(self, number):
        return str(number).split('.')

    def split_by_3(self, number):
        """
        starting here, it groups the number by three from the tail
        '1234567' -> (('1',),('234',),('567',))
        :param number:str
        :rtype:tuple
        """
        blocks = ()
        length = len(number)

        if length < 3:
            blocks += ((number,),)
        else:
            len_of_first_block = length % 3

            if len_of_first_block > 0:
                first_block = number[0:len_of_first_block],
                blocks += first_block,

            for i in range(len_of_first_block, length, 3):
                next_block = (number[i:i + 3],),
                blocks += next_block

        return blocks

    def spell(self, blocks):
        """
        it adds the list of spelling to the blocks
        (
        ('1',),('034',)) -> (('1',['satu']),('234',['tiga', 'puluh', 'empat'])
        )
        :param blocks: tuple
        :rtype: tuple
        """
        word_blocks = ()
        first_block = blocks[0]
        if len(first_block[0]) == 1:
            if first_block[0] == '0':
                spelling = ['nol']
            else:
                spelling = self.BASE[int(first_block[0])]
        elif len(first_block[0]) == 2:
            spelling = self.puluh(first_block[0])
        else:
            spelling = (
                self.ratus(first_block[0][0]) + self.puluh(first_block[0][1:3])
                )

        word_blocks += (first_block[0], spelling),

        for block in blocks[1:]:
            spelling = self.ratus(block[0][0]) + self.puluh(block[0][1:3])
            block += spelling,
            word_blocks += block,

        return word_blocks

    def ratus(self, number):
        # it is used to spell
        if number == '1':
            return ['seratus']
        elif number == '0':
            return []
        else:
            return self.BASE[int(number)] + ['ratus']

    def puluh(self, number):
        # it is used to spell
        if number[0] == '1':
            if number[1] == '0':
                return ['sepuluh']
            elif number[1] == '1':
                return ['sebelas']
            else:
                return self.BASE[int(number[1])] + ['belas']
        elif number[0] == '0':
            return self.BASE[int(number[1])]
        else:
            return (
                self.BASE[int(number[0])] + ['puluh']
                + self.BASE[int(number[1])]
            )

    def spell_float(self, float_part):
        # spell the float number
        word_list = []
        for n in float_part:
            if n == '0':
                word_list += ['nol']
                continue
            word_list += self.BASE[int(n)]
        return ' '.join(['', 'koma'] + word_list)

    def join(self, word_blocks, float_part):
        """
        join the words by first join lists in the tuple
        :param word_blocks: tuple
        :rtype: str
        """
        word_list = []
        length = len(word_blocks) - 1
        first_block = word_blocks[0],
        start = 0

        if length == 1 and first_block[0][0] == '1':
            word_list += ['seribu']
            start = 1

        for i in range(start, length + 1, 1):
            word_list += word_blocks[i][1]
            if not word_blocks[i][1]:
                continue
            if i == length:
                break
            word_list += [self.TENS_TO[(length - i) * 3]]

        return ' '.join(word_list) + float_part

    def to_cardinal(self, number):
        if number >= self.max_num:
            raise OverflowError(self.errmsg_toobig % (number, self.max_num))
        minus = ''
        if number < 0:
            minus = 'min '
        float_word = ''
        n = self.split_by_koma(abs(number))
        if len(n) == 2:
            float_word = self.spell_float(n[1])
        return minus + self.join(self.spell(self.split_by_3(n[0])), float_word)

    def to_ordinal(self, number):
        self.verify_ordinal(number)
        out_word = self.to_cardinal(number)
        if out_word == "satu":
            return "pertama"
        return "ke" + out_word

    def to_ordinal_num(self, number):
        self.verify_ordinal(number)
        return "ke-" + str(number)

    def to_currency(self, value):
        return self.to_cardinal(value) + " rupiah"

    def to_year(self, value):
        return self.to_cardinal(value)

    def verify_ordinal(self, value):
        if not value == int(value):
            raise TypeError(self.errmsg_floatord % value)
        if not abs(value) == value:
            raise TypeError(self.errmsg_negord % value)
