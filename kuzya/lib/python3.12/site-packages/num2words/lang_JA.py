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

from __future__ import division, print_function, unicode_literals

from .base import Num2Word_Base
from .compat import strtype, to_s
from .currency import parse_currency_parts, prefix_currency


def select_text(text, reading=False, prefer=None):
    """Select the correct text from the Japanese number, reading and
    alternatives"""
    # select kanji number or kana reading
    if reading:
        text = text[1]
    else:
        text = text[0]

    # select the preferred one or the first one from multiple alternatives
    if not isinstance(text, strtype):
        common = set(text) & set(prefer or set())
        if len(common) == 1:
            text = common.pop()
        else:
            text = text[0]

    return text


def rendaku_merge_pairs(lpair, rpair):
    """Merge lpair < rpair while applying semi-irregular rendaku rules"""
    ltext, lnum = lpair
    rtext, rnum = rpair
    if lnum > rnum:
        raise ValueError

    if rpair == ("ひゃく", 100):
        if lpair == ("さん", 3):
            rtext = "びゃく"
        elif lpair == ("ろく", 6):
            ltext = "ろっ"
            rtext = "ぴゃく"
        elif lpair == ("はち", 8):
            ltext = "はっ"
            rtext = "ぴゃく"
    elif rpair == ("せん", 1000):
        if lpair == ("さん", 3):
            rtext = "ぜん"
        elif lpair == ("はち", 8):
            ltext = "はっ"
    elif rpair == ("ちょう", 10**12):
        if lpair == ("いち", 1):
            ltext = "いっ"
        elif lpair == ("はち", 8):
            ltext = "はっ"
        elif lpair == ("じゅう", 10):
            ltext = "じゅっ"
    elif rpair == ("けい", 10**16):
        if lpair == ("いち", 1):
            ltext = "いっ"
        elif lpair == ("ろく", 6):
            ltext = "ろっ"
        elif lpair == ("はち", 8):
            ltext = "はっ"
        elif lpair == ("じゅう", 10):
            ltext = "じゅっ"
        elif lpair == ("ひゃく", 100):
            ltext = "ひゃっ"

    return ("%s%s" % (ltext, rtext), lnum * rnum)


# Source: https://www.sljfaq.org/afaq/era-list.html
# if there are multiple eras for the same year, use the last one
ERA_START = [
    (645, ("大化", "たいか")),
    (650, ("白雉", "はくち")),
    (686, ("朱鳥", "しゅちょう")),
    (701, ("大宝", "たいほう")),
    (704, ("慶雲", "けいうん")),
    (708, ("和銅", "わどう")),
    (715, ("霊亀", "れいき")),
    (717, ("養老", "ようろう")),
    (724, ("神亀", "じんき")),
    (729, ("天平", "てんぴょう")),
    (749, ("天平感宝", "てんぴょうかんぽう")),
    (749, ("天平勝宝", "てんぴょうしょうほう")),
    (757, ("天平宝字", "てんぴょうじょうじ")),
    (765, ("天平神護", "てんぴょうじんご")),
    (767, ("神護景雲", "じんごけいうん")),
    (770, ("宝亀", "ほうき")),
    (781, ("天応", "てんおう")),
    (782, ("延暦", "えんりゃく")),
    (806, ("大同", "だいどう")),
    (810, ("弘仁", "こうにん")),
    (823, ("天長", "てんちょう")),
    (834, ("承和", "じょうわ")),
    (848, ("嘉祥", "かしょう")),
    (851, ("仁寿", "にんじゅ")),
    (855, ("斉衡", "さいこう")),
    (857, ("天安", "てんあん")),
    (859, ("貞観", "じょうがん")),
    (877, ("元慶", "がんぎょう")),
    (885, ("仁和", "にんな")),
    (889, ("寛平", "かんぴょう")),
    (898, ("昌泰", "しょうたい")),
    (901, ("延喜", "えんぎ")),
    (923, ("延長", "えんちょう")),
    (931, ("承平", "じょうへい")),
    (938, ("天慶", "てんぎょう")),
    (947, ("天暦", "てんりゃく")),
    (957, ("天徳", "てんとく")),
    (961, ("応和", "おうわ")),
    (964, ("康保", "こうほう")),
    (968, ("安和", "あんな")),
    (970, ("天禄", "てんろく")),
    (974, ("天延", "てんえん")),
    (976, ("貞元", "じょうげん")),
    (979, ("天元", "てんげん")),
    (983, ("永観", "えいかん")),
    (985, ("寛和", "かんな")),
    (987, ("永延", "えいえん")),
    (989, ("永祚", "えいそ")),
    (990, ("正暦", "しょうりゃく")),
    (995, ("長徳", "ちょうとく")),
    (999, ("長保", "ちょうほう")),
    (1004, ("寛弘", "かんこう")),
    (1013, ("長和", "ちょうわ")),
    (1017, ("寛仁", "かんにん")),
    (1021, ("治安", "じあん")),
    (1024, ("万寿", "まんじゅ")),
    (1028, ("長元", "ちょうげん")),
    (1037, ("長暦", "ちょうりゃく")),
    (1040, ("長久", "ちょうきゅう")),
    (1045, ("寛徳", "かんとく")),
    (1046, ("永承", "えいしょう")),
    (1053, ("天喜", "てんぎ")),
    (1058, ("康平", "こうへい")),
    (1065, ("治暦", "じりゃく")),
    (1069, ("延久", "えんきゅう")),
    (1074, ("承保", "じょうほう")),
    (1078, ("承暦", "じょうりゃく")),
    (1081, ("永保", "えいほう")),
    (1084, ("応徳", "おうとく")),
    (1087, ("寛治", "かんじ")),
    (1095, ("嘉保", "かほう")),
    (1097, ("永長", "えいちょう")),
    (1098, ("承徳", "じょうとく")),
    (1099, ("康和", "こうわ")),
    (1104, ("長治", "ちょうじ")),
    (1106, ("嘉承", "かじょう")),
    (1108, ("天仁", "てんにん")),
    (1110, ("天永", "てんねい")),
    (1113, ("永久", "えいきゅう")),
    (1118, ("元永", "げんえい")),
    (1120, ("保安", "ほうあん")),
    (1124, ("天治", "てんじ")),
    (1126, ("大治", "だいじ")),
    (1131, ("天承", "てんしょう")),
    (1132, ("長承", "ちょうしょう")),
    (1135, ("保延", "ほうえん")),
    (1141, ("永治", "えいじ")),
    (1142, ("康治", "こうじ")),
    (1144, ("天養", "てんよう")),
    (1145, ("久安", "きゅうあん")),
    (1151, ("仁平", "にんぺい")),
    (1154, ("久寿", "きゅうじゅ")),
    (1156, ("保元", "ほうげん")),
    (1159, ("平治", "へいじ")),
    (1160, ("永暦", "えいりゃく")),
    (1161, ("応保", "おうほう")),
    (1163, ("長寛", "ちょうかん")),
    (1165, ("永万", "えいまん")),
    (1166, ("仁安", "にんあん")),
    (1169, ("嘉応", "かおう")),
    (1171, ("承安", "しょうあん")),
    (1175, ("安元", "あんげん")),
    (1177, ("治承", "じしょう")),
    (1181, ("養和", "ようわ")),
    (1182, ("寿永", "じゅえい")),
    (1184, ("元暦", "げんりゃく")),
    (1185, ("文治", "ぶんじ")),
    (1190, ("建久", "けんきゅう")),
    (1199, ("正治", "しょうじ")),
    (1201, ("建仁", "けんにん")),
    (1204, ("元久", "げんきゅう")),
    (1206, ("建永", "けんえい")),
    (1207, ("承元", "じょうげん")),
    (1211, ("建暦", "けんりゃく")),
    (1214, ("建保", "けんぽう")),
    (1219, ("承久", "じょうきゅう")),
    (1222, ("貞応", "じょうおう")),
    (1225, ("元仁", "げんにん")),
    (1225, ("嘉禄", "かろく")),
    (1228, ("安貞", "あんてい")),
    (1229, ("寛喜", "かんき")),
    (1232, ("貞永", "じょうえい")),
    (1233, ("天福", "てんぷく")),
    (1235, ("文暦", "ぶんりゃく")),
    (1235, ("嘉禎", "かてい")),
    (1239, ("暦仁", "りゃくにん")),
    (1239, ("延応", "えんおう")),
    (1240, ("仁治", "にんじ")),
    (1243, ("寛元", "かんげん")),
    (1247, ("宝治", "ほうじ")),
    (1249, ("建長", "けんちょう")),
    (1256, ("康元", "こうげん")),
    (1257, ("正嘉", "しょうか")),
    (1259, ("正元", "しょうげん")),
    (1260, ("文応", "ぶんおう")),
    (1261, ("弘長", "こうちょう")),
    (1264, ("文永", "ぶんえい")),
    (1275, ("健治", "けんじ")),
    (1278, ("弘安", "こうあん")),
    (1288, ("正応", "しょうおう")),
    (1293, ("永仁", "えいにん")),
    (1299, ("正安", "しょうあん")),
    (1303, ("乾元", "けんげん")),
    (1303, ("嘉元", "かげん")),
    (1307, ("徳治", "とくじ")),
    (1308, ("延慶", "えんきょう")),
    (1311, ("応長", "おうちょう")),
    (1312, ("正和", "しょうわ")),
    (1317, ("文保", "ぶんぽう")),
    (1319, ("元応", "げんおう")),
    (1321, ("元亨", "げんこう")),
    (1325, ("正中", "しょうちゅ")),
    (1326, ("嘉暦", "かりゃく")),
    (1329, ("元徳", "げんとく")),
    (1331, ("元弘", "げんこう")),
    (1332, ("正慶", "しょうけい")),
    (1334, ("建武", "けんむ")),
    (1336, ("延元", "えいげん")),
    (1338, ("暦応", "りゃくおう")),
    (1340, ("興国", "こうこく")),
    (1342, ("康永", "こうえい")),
    (1345, ("貞和", "じょうわ")),
    (1347, ("正平", "しょうへい")),
    (1350, ("観応", "かんおう")),
    (1352, ("文和", "ぶんな")),
    (1356, ("延文", "えんぶん")),
    (1361, ("康安", "こうあん")),
    (1362, ("貞治", "じょうじ")),
    (1368, ("応安", "おうあん")),
    (1370, ("建徳", "けんとく")),
    (1372, ("文中", "ぶんちゅう")),
    (1375, ("永和", "えいわ")),
    (1375, ("天授", "てんじゅ")),
    (1379, ("康暦", "こうりゃく")),
    (1381, ("永徳", "えいとく")),
    (1381, ("弘和", "こうわ")),
    (1384, ("至徳", "しとく")),
    (1384, ("元中", "げんちゅう")),
    (1387, ("嘉慶", "かけい")),
    (1389, ("康応", "こうおう")),
    (1390, ("明徳", "めいとく")),
    (1394, ("応永", "おうえい")),
    (1428, ("正長", "しょうちょう")),
    (1429, ("永享", "えいきょう")),
    (1441, ("嘉吉", "かきつ")),
    (1444, ("文安", "ぶんあん")),
    (1449, ("宝徳", "ほうとく")),
    (1452, ("享徳", "きょうとく")),
    (1455, ("康正", "こうしょう")),
    (1457, ("長禄", "ちょうろく")),
    (1461, ("寛正", "かんしょう")),
    (1466, ("文正", "ぶんしょう")),
    (1467, ("応仁", "おうにん")),
    (1469, ("文明", "ぶんめい")),
    (1487, ("長享", "ちょうきょう")),
    (1489, ("延徳", "えんとく")),
    (1492, ("明応", "めいおう")),
    (1501, ("文亀", "ぶんき")),
    (1504, ("永正", "えいしょう")),
    (1521, ("大永", "だいえい")),
    (1528, ("享禄", "きょうろく")),
    (1532, ("天文", "てんぶん")),
    (1555, ("弘治", "こうじ")),
    (1558, ("永禄", "えいろく")),
    (1570, ("元亀", "げんき")),
    (1573, ("天正", "てんしょう")),
    (1593, ("文禄", "ぶんろく")),
    (1596, ("慶長", "けいちょう")),
    (1615, ("元和", "げんな")),
    (1624, ("寛永", "かんえい")),
    (1645, ("正保", "しょうほう")),
    (1648, ("慶安", "けいあん")),
    (1652, ("承応", "じょうおう")),
    (1655, ("明暦", "めいれき")),
    (1658, ("万治", "まんじ")),
    (1661, ("寛文", "かんぶん")),
    (1673, ("延宝", "えんぽう")),
    (1681, ("天和", "てんな")),
    (1684, ("貞享", "じょうきょう")),
    (1688, ("元禄", "げんろく")),
    (1704, ("宝永", "ほうえい")),
    (1711, ("正徳", "しょうとく")),
    (1716, ("享保", "きょうほう")),
    (1736, ("元文", "げんぶん")),
    (1741, ("寛保", "かんぽう")),
    (1744, ("延享", "えんきょう")),
    (1748, ("寛延", "かんえん")),
    (1751, ("宝暦", "ほうれき")),
    (1764, ("明和", "めいわ")),
    (1773, ("安永", "あんえい")),
    (1781, ("天明", "てんめい")),
    (1801, ("寛政", "かんせい")),
    (1802, ("享和", "きょうわ")),
    (1804, ("文化", "ぶんか")),
    (1818, ("文政", "ぶんせい")),
    (1831, ("天保", "てんぽう")),
    (1845, ("弘化", "こうか")),
    (1848, ("嘉永", "かえい")),
    (1855, ("安政", "あんせい")),
    (1860, ("万延", "まんえい")),
    (1861, ("文久", "ぶんきゅう")),
    (1864, ("元治", "げんじ")),
    (1865, ("慶応", "けいおう")),
    (1868, ("明治", "めいじ")),
    (1912, ("大正", "たいしょう")),
    (1926, ("昭和", "しょうわ")),
    (1989, ("平成", "へいせい")),
    (2019, ("令和", "れいわ")),
]


class Num2Word_JA(Num2Word_Base):
    CURRENCY_FORMS = {
        'JPY': (('円', 'えん'), ()),
    }

    def set_high_numwords(self, high):
        max = 4 * len(high)
        for word, n in zip(high, range(max, 0, -4)):
            self.cards[10 ** n] = word

    def setup(self):
        self.negword = "マイナス"
        self.pointword = ("点", "てん")
        self.exclude_title = ["点", "マイナス"]

        self.high_numwords = [
            ("万", "まん"),    # 10**4 man
            ("億", "おく"),    # 10**8 oku
            ("兆", "ちょう"),  # 10**12 chō
            ("京", "けい"),    # 10**16 kei
            ("垓", "がい"),    # 10**20 gai
            ("秭", "し"),      # 10**24 shi
            ("穣", "じょう"),  # 10**28 jō
            ("溝", "こう"),    # 10**32 kō
            ("澗", "かん"),    # 10**36 kan
            ("正", "せい"),    # 10**40 sei
            ("載", "さい"),    # 10**44 sai
            ("極", "ごく"),    # 10**48 goku
        ]

        self.high_numwords.reverse()

        self.mid_numwords = [
            (1000, ("千", "せん")),
            (100, ("百", "ひゃく")),
        ]

        self.low_numwords = [
            ("十", "じゅう"),                  # 10 jū
            ("九", "きゅう"),                  # 9 kyū
            ("八", "はち"),                    # 8 hachi
            ("七", ("なな", "しち")),          # 7 nana, shichi
            ("六", "ろく"),                    # 6 roku
            ("五", "ご"),                      # 5 go
            ("四", ("よん", "し")),            # 4 yon, shi
            ("三", "さん"),                    # 3 san
            ("二", "に"),                      # 2 ni
            ("一", "いち"),                    # 1 ichi
            # both are alternatives, 零 doesn't map to ゼロ or 〇 to れい
            (("零", "〇"), ("ゼロ", "れい")),  # 0 ZERO, rei
        ]

    def merge(self, lpair, rpair):
        ltext, lnum = lpair
        rtext, rnum = rpair

        fmt = "%s%s"
        # ignore lpair if lnum is 1 and rnum is less than 10000
        if lnum == 1 and rnum < 10000:
            return rpair
        # rnum is added to lnum
        elif lnum > rnum:
            return (fmt % (ltext, rtext), lnum + rnum)
        # rnum is multiplied by lnum
        elif lnum < rnum:
            return rendaku_merge_pairs(lpair, rpair)

    def _ordinal_suffix(self, reading, counter):
        if reading:
            if counter == "番":
                return "ばんめ"
            else:
                raise NotImplementedError(
                    "Reading not implemented for %s" % counter)
        else:
            return counter + "目"

    def to_ordinal(self, value, reading=False, prefer=None, counter="番"):
        self.verify_ordinal(value)
        base = self.to_cardinal(value, reading=reading, prefer=prefer)
        return "%s%s" % (base, self._ordinal_suffix(reading, counter))

    def to_ordinal_num(self, value, reading=False, counter="番"):
        return "%s%s" % (value, self._ordinal_suffix(reading, counter))

    def to_year(self, val, suffix=None, longval=True, reading=False,
                prefer=None, era=True):
        year = val
        # Gregorian calendar
        if not era:
            prefix = ""
            if year < 0:
                year = abs(year)
                prefix = "きげんぜん" if reading else "紀元前"

            year_words = self.to_cardinal(year, reading=reading, prefer=prefer)
            if reading and year % 10 == 9:
                year_words = year_words[:-3] + "く"

            return "%s%s%s" % (prefix, year_words, "ねん" if reading else "年")

        # Era calendar (default)
        min_year = ERA_START[0][0]
        last_era_idx = len(ERA_START) - 1
        if year < min_year:
            raise ValueError(
                "Can't convert years less than %s to era" % min_year)

        first = 0
        last = last_era_idx
        era_idx = None
        while era_idx is None:
            mid = (first + last) // 2
            if mid == last_era_idx or (ERA_START[mid][0] <= year and
                                       ERA_START[mid + 1][0] > year):
                era_idx = mid
                # if an era lasting less than a year is preferred, choose it
                if prefer:
                    i = mid - 1
                    while i >= 0 and ERA_START[i][0] == year:
                        # match kanji or hiragana
                        if set(ERA_START[i][1]) & set(prefer):
                            era_idx = i
                            break
                        i -= 1

            # ends up at the last index where year >= ERA_START[mid][0]
            if year < ERA_START[mid][0]:
                last = mid - 1
            else:
                first = mid + 1

        era = ERA_START[era_idx]
        era_name = era[1][0]
        era_year = year - era[0] + 1
        fmt = "%s%s年"
        if reading == "arabic":
            era_year_words = str(era_year)
        elif reading:
            era_name = era[1][1]
            era_year_words = (self.to_cardinal(era_year, reading=True,
                                               prefer=prefer)
                              if era_year != 1 else "がん")
            if era_year % 10 == 9:
                era_year_words = era_year_words[:-3] + "く"
            fmt = "%s%sねん"
        else:
            era_year_words = (self.to_cardinal(era_year, reading=False,
                                               prefer=prefer)
                              if era_year != 1 else "元")

        return fmt % (era_name, era_year_words)

    def to_currency(self, val, currency="JPY", cents=False, separator="",
                    adjective=False, reading=False, prefer=None):
        left, right, is_negative = parse_currency_parts(
            val, is_int_with_cents=cents)

        try:
            cr1, cr2 = self.CURRENCY_FORMS[currency]
            if (cents or abs(val) != left) and not cr2:
                raise ValueError('Decimals not supported for "%s"' % currency)
        except KeyError:
            raise NotImplementedError(
                'Currency code "%s" not implemented for "%s"' %
                (currency, self.__class__.__name__))

        if adjective and currency in self.CURRENCY_ADJECTIVES:
            cr1 = prefix_currency(self.CURRENCY_ADJECTIVES[currency], cr1)

        minus_str = self.negword if is_negative else ""

        return '%s%s%s%s%s' % (
            minus_str,
            self.to_cardinal(left, reading=reading, prefer=prefer),
            cr1[1] if reading else cr1[0],
            self.to_cardinal(right, reading=reading, prefer=prefer)
            if cr2 else '',
            (cr2[1] if reading else cr2[0]) if cr2 else '',
        )

    def splitnum(self, value, reading, prefer):
        for elem in self.cards:
            if elem > value:
                continue

            out = []
            if value == 0:
                div, mod = 1, 0
            else:
                div, mod = divmod(value, elem)

            if div == 1:
                out.append((select_text(self.cards[1], reading, prefer), 1))
            else:
                if div == value:  # The system tallies, eg Roman Numerals
                    return [(
                        div * select_text(self.cards[elem], reading, prefer),
                        div * elem)]
                out.append(self.splitnum(div, reading, prefer))

            out.append((select_text(self.cards[elem], reading, prefer), elem))

            if mod:
                out.append(self.splitnum(mod, reading, prefer))

            return out

    def to_cardinal(self, value, reading=False, prefer=None):
        try:
            assert int(value) == value
        except (ValueError, TypeError, AssertionError):
            return self.to_cardinal_float(value, reading=reading,
                                          prefer=prefer)

        out = ""
        if value < 0:
            value = abs(value)
            out = self.negword

        if value >= self.MAXVAL:
            raise OverflowError(self.errmsg_toobig % (value, self.MAXVAL))

        val = self.splitnum(value, reading, prefer)
        words, _ = self.clean(val)
        return self.title(out + words)

    def to_cardinal_float(self, value, reading=False, prefer=None):
        prefer = prefer or ["れい"]
        try:
            float(value) == value
        except (ValueError, TypeError, AssertionError):
            raise TypeError(self.errmsg_nonnum % value)

        pre, post = self.float2tuple(float(value))

        post = str(post)
        post = '0' * (self.precision - len(post)) + post

        out = [self.to_cardinal(pre, reading=reading, prefer=prefer)]
        if self.precision:
            out.append(self.title(self.pointword[1 if reading else 0]))

        for i in range(self.precision):
            curr = int(post[i])
            out.append(to_s(
                self.to_cardinal(curr, reading=reading, prefer=prefer)))

        return "".join(out)
