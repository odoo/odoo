# -*- encoding: utf-8 -*-
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

from .lang_EU import Num2Word_EU


class Num2Word_KN(Num2Word_EU):
    def set_high_numwords(self, high):
        for n, word in self.high_numwords:
            self.cards[10**n] = word

    def setup(self):
        self.low_numwords = [
            "ತೊಂಬತ್ತೊಂಬತ್ತು",
            "ತೊಂಬತ್ತೆಂಟು",
            "ತೊಂಬತ್ತೇಳು",
            "ತೊಂಬತ್ತಾರು",
            "ತೊಂಬತ್ತೈದು",
            "ತೊಂಬತ್ತ ನಾಲ್ಕು",
            "ತೊಂಬತ್ತ ಮೂರು",
            "ತೊಂಬತ್ತೆರಡು",
            "ತೊಂಬತ್ತೊಂದು",
            "ತೊಂಬತ್ತು",
            "ಎಂಬತ್ತೊಂಬತ್ತು",
            "ಎಂಬತ್ತೆಂಟು",
            "ಎಂಬತ್ತೇಳು",
            "ಎಂಬತ್ತಾರು",
            "ಎಂಬತ್ತೈದು",
            "ಎಂಬತ್ತ್ ನಾಲ್ಕು",
            "ಎಂಬತ್ತ್ ಮೂರು",
            "ಎಂಬತ್ತೆರಡು",
            "ಎಂಬತ್ತೊಂದು",
            "ಎಂಬತ್ತು",
            "ಎಪ್ಪತ್ತೊಂಬತ್ತು",
            "ಎಪ್ಪತ್ತೆಂಟು",
            "ಎಪ್ಪತ್ತೇಳು",
            "ಎಪ್ಪತ್ತಾರು",
            "ಎಪ್ಪತ್ತೈದು",
            "ಎಪ್ಪತ್ತ್ ನಾಲ್ಕು",
            "ಎಪ್ಪತ್ತ್ ಮೂರು",
            "ಎಪ್ಪತ್ತೆರಡು",
            "ಎಪ್ಪತ್ತೊಂದು",
            "ಎಪ್ಪತ್ತು",
            "ಅರವತ್ತೊಂಬತ್ತು",
            "ಅರವತ್ತೆಂಟು",
            "ಅರವತ್ತೇಳು",
            "ಅರವತ್ತಾರು",
            "ಅರವತ್ತೈದು",
            "ಅರವತ್ತ್ ನಾಲ್ಕು",
            "ಅರವತ್ತ್ ಮೂರು",
            "ಅರವತ್ತೆರಡು",
            "ಅರವತ್ತೊಂದು",
            "ಅರವತ್ತು",
            "ಐವತ್ತೊಂಬತ್ತು",
            "ಐವತ್ತೆಂಟು",
            "ಐವತ್ತೇಳು",
            "ಐವತ್ತಾರು",
            "ಐವತ್ತೈದು",
            "ಐವತ್ತ್ನಾಲ್ಕು",
            "ಐವತ್ತಮೂರು",
            "ಐವತ್ತೆರಡು",
            "ಐವತ್ತೊಂದು",
            "ಐವತ್ತು",
            "ನಲವತ್ತೊಂಬತ್ತು",
            "ನಲವತ್ತೆಂಟು",
            "ನಲವತ್ತೇಳು",
            "ನಲವತ್ತಾರು",
            "ನಲವತ್ತೈದು",
            "ನಲವತ್ತ್ ನಾಲ್ಕು",
            "ನಲವತ್ತ್ ಮೂರು",
            "ನಲವತ್ತ್ ಎರಡು",
            "ನಲವತ್ತೊಂದು",
            "ನಲವತ್ತು",
            "ಮೂವತ್ತ್ ಒಂಬತ್ತು",
            "ಮೂವತ್ಎಂಟು",
            "ಮೂವತ್ಏಳು",
            "ಮೂವತ್ಆರು",
            "ಮೂವತ್ತ್ ಐದು",
            "ಮೂವತ್ತ್ ನಾಲ್ಕು",
            "ಮೂವತ್ತ್ ಮೂರು",
            "ಮೂವತ್ತ್ಎರಡು",
            "ಮೂವತ್ತ್ಒಂದು",
            "ಮೂವತ್ತು",
            "ಇಪ್ಪತ್ತ್ಒಂಬತ್ತು",
            "ಇಪ್ಪತ್ತ್ಎಂಟು",
            "ಇಪ್ಪತ್ತ್ಏಳು",
            "ಇಪ್ಪತ್ತ್ಆರು",
            "ಇಪ್ಪತ್ತ್ ಐದು",
            "ಇಪ್ಪತ್ತ್ ನಾಲ್ಕು",
            "ಇಪ್ಪತ್ತ್ ಮೂರು",
            "ಇಪ್ಪತ್ತ್ ಎರಡು",
            "ಇಪ್ಪತ್ತ್ ಒಂದು",
            "ಇಪ್ಪತ್ತು",
            "ಹತ್ತೊಂಬತ್ತು",
            "ಹದಿನೆಂಟು",
            "ಹದಿನೇಳು",
            "ಹದಿನಾರು",
            "ಹದಿನೈದು",
            "ಹದಿನಾಲ್ಕು",
            "ಹದಿಮೂರು",
            "ಹನ್ನೆರಡು",
            "ಹನ್ನೊಂದು",
            "ಹತ್ತು",
            "ಒಂಬತ್ತು",
            "ಎಂಟು",
            "ಏಳು",
            "ಆರು",
            "ಐದು",
            "ನಾಲ್ಕು",
            "ಮೂರು",
            "ಎರಡು",
            "ಒಂದು",
            "ಸೊನ್ನೆ",
        ]

        self.mid_numwords = [(100, "ನೂರು")]

        self.high_numwords = [(7, "ಕೋಟಿ"), (5, "ಒಂದು ಲಕ್ಷ"), (3, "ಸಾವಿರ")]

        self.pointword = "ಬಿಂದು"

        self.modifiers = [
            "್",
            "ಾ",
            "ಿ",
            "ೀ",
            "ೀ",
            "ು",
            "ೂ",
            "ೃ",
            "ೆ",
            "ೇ",
            "ೈ",
            "ೊ",
            "ೋ",
            "ೌ",
            "ೕ",
        ]

    def merge(self, lpair, rpair):
        ltext, lnum = lpair
        rtext, rnum = rpair
        if lnum == 1 and rnum < 100:
            return (rtext, rnum)
        elif 100 > lnum > rnum:
            return ("%s-%s" % (ltext, rtext), lnum + rnum)
        elif lnum >= 100 > rnum:
            if ltext[-1] in self.modifiers:
                return ("%s %s" % (ltext[:-1], rtext), lnum + rnum)
            else:
                return ("%s %s" % (ltext + "ದ", rtext), lnum + rnum)
        elif rnum > lnum:
            return ("%s %s" % (ltext, rtext), lnum * rnum)
        return ("%s %s" % (ltext, rtext), lnum + rnum)

    def to_ordinal_num(self, value):
        self.verify_ordinal(value)
        return "%s%s" % (value, self.to_ordinal(value))

    def to_ordinal(self, value):
        self.verify_ordinal(value)
        outwords = self.to_cardinal(value)
        if outwords[-1] in self.modifiers:
            outwords = outwords[:-1]
        ordinal_num = outwords + "ನೇ"
        return ordinal_num
