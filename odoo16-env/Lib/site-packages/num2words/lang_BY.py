# Copyright (c) 2003, Taro Ogawa.  All Rights Reserved.
# Copyright (c) 2013, Savoir-faire Linux inc.  All Rights Reserved.
# Copyright (c) 2022, Sergei Ruzki.  All Rights Reserved.

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
from .utils import get_digits, splitbyx

ZERO = "нуль"

ONES_FEMININE = {
    1: "адна",
    2: "дзве",
    3: "тры",
    4: "чатыры",
    5: "пяць",
    6: "шэсць",
    7: "сем",
    8: "восем",
    9: "дзевяць",
}

ONES = {
    "f": {
        1: "адна",
        2: "дзве",
        3: "тры",
        4: "чатыры",
        5: "пяць",
        6: "шэсць",
        7: "сем",
        8: "восем",
        9: "дзевяць",
    },
    "m": {
        1: "адзін",
        2: "два",
        3: "тры",
        4: "чатыры",
        5: "пяць",
        6: "шэсць",
        7: "сем",
        8: "восем",
        9: "дзевяць",
    },
    "n": {
        1: "адно",
        2: "два",
        3: "тры",
        4: "чатыры",
        5: "пяць",
        6: "шэсць",
        7: "сем",
        8: "восем",
        9: "дзевяць",
    },
}

TENS = {
    0: "дзесяць",
    1: "адзінаццаць",
    2: "дванаццаць",
    3: "трынаццаць",
    4: "чатырнаццаць",
    5: "пятнаццаць",
    6: "шаснаццаць",
    7: "сямнаццаць",
    8: "васямнаццаць",
    9: "дзевятнаццаць",
}

TWENTIES = {
    2: "дваццаць",
    3: "трыццаць",
    4: "сорак",
    5: "пяцьдзясят",
    6: "шэсцьдзясят",
    7: "семдзесят",
    8: "восемдзесят",
    9: "дзевяноста",
}

HUNDREDS = {
    1: "сто",
    2: "дзвесце",
    3: "трыста",
    4: "чатырыста",
    5: "пяцьсот",
    6: "шэсцьсот",
    7: "семсот",
    8: "восемсот",
    9: "дзевяцьсот",
}

THOUSANDS = {
    1: ("тысяча", "тысячы", "тысяч"),  # 10^3
    2: ("мільён", "мільёны", "мільёнаў"),  # 10^6
    3: ("мільярд", "мільярды", "мільярдаў"),  # 10^9
    4: ("трыльён", "трыльёны", "трыльёнаў"),  # 10^12
    5: ("квадрыльён", "квадрыльёны", "квадрыльёнаў"),  # 10^15
    6: ("квінтыльён", "квінтыльёны", "квінтыльёнаў"),  # 10^18
    7: ("секстыльён", "секстыльёны", "секстыльёнаў"),  # 10^21
    8: ("сэптыльён", "сэптыльёны", "сэптыльёнаў"),  # 10^24
    9: ("актыльён", "актыльёны", "актыльёнаў"),  # 10^27
    10: ("нанільён", "нанільёны", "нанільёнаў"),  # 10^30
}


class Num2Word_BY(Num2Word_Base):
    CURRENCY_FORMS = {
        "RUB": (
            ("расійскі рубель", "расійскія рублі", "расійскіх рублёў"),
            ("капейка", "капейкі", "капеек"),
        ),
        "EUR": (("еўра", "еўра", "еўра"), ("цэнт", "цэнты", "цэнтаў")),
        "USD": (("долар", "долары", "долараў"), ("цэнт", "цэнты", "цэнтаў")),
        "UAH": (
            ("грыўна", "грыўны", "грыўнаў"),
            ("капейка", "капейкі", "капеек"),
        ),
        "KZT": (("тэнге", "тэнге", "тэнге"), ("тыйін", "тыйіны", "тыйінаў")),
        "BYN": (
            ("беларускі рубель", "беларускія рублі", "беларускіх рублёў"),
            ("капейка", "капейкі", "капеек"),
        ),
        "UZS": (("сум", "сумы", "сумаў"), ("тыйін", "тыйіны", "тыйінаў")),
    }

    def setup(self):
        self.negword = "мінус"
        self.pointword = "коска"
        self.ords = {
            "нуль": "нулявы",
            "адзін": "першы",
            "два": "другі",
            "тры": "трэці",
            "чатыры": "чацвёрты",
            "пяць": "пяты",
            "шэсць": "шосты",
            "сем": "сёмы",
            "восем": "восьмы",
            "дзевяць": "дзявяты",
            "сто": "соты",
            "тысяча": "тысячны",
        }

        self.ords_adjective = {
            "адзін": "адна",
            "адна": "адна",
            "дзве": "двух",
            "тры": "трох",
            "чатыры": "чатырох",
            "пяць": "пяці",
            "шэсць": "шасці",
            "сем": "сямі",
            "восем": "васьмі",
            "дзевяць": "дзевяцi",
            "сто": "ста",
        }

    def to_cardinal(self, number, gender="m"):
        n = str(number).replace(",", ".")
        if "." in n:
            left, right = n.split(".")
            if set(right) == {"0"}:
                leading_zero_count = 0
            else:
                leading_zero_count = len(right) - len(right.lstrip("0"))

            decimal_part = (ZERO + " ") * leading_zero_count + self._int2word(
                int(right), gender
            )
            return "{} {} {}".format(
                self._int2word(int(left), gender), self.pointword, decimal_part
            )
        else:
            return self._int2word(int(n), gender)

    def pluralize(self, n, forms):
        if n % 100 < 10 or n % 100 > 20:
            if n % 10 == 1:
                form = 0
            elif 5 > n % 10 > 1:
                form = 1
            else:
                form = 2
        else:
            form = 2
        return forms[form]

    def to_ordinal(self, number, gender="m"):
        self.verify_ordinal(number)
        outwords = self.to_cardinal(number, gender).split(" ")
        lastword = outwords[-1].lower()
        try:
            if len(outwords) > 1:
                if outwords[-2] in self.ords_adjective:
                    outwords[-2] = self.ords_adjective.get(
                        outwords[-2], outwords[-2]
                    )
                elif outwords[-2] == "дзесяць":
                    outwords[-2] = outwords[-2][:-1] + "і"
            if len(outwords) == 3:
                if outwords[-3] in ["адзін", "адна"]:
                    outwords[-3] = ""
            lastword = self.ords[lastword]
        except KeyError:
            if lastword[:-3] in self.ords_adjective:
                lastword = (
                    self.ords_adjective.get(lastword[:-3], lastword) + "соты"
                )
            elif lastword[-5:] == "шэсць":
                lastword = "шосты"
            elif lastword[-7:] == "дзесяць":
                lastword = "дзясяты"
            elif lastword[-9:] == "семдзесят":
                lastword = "сямідзясяты"
            elif lastword[-1] == "ь" or lastword[-2] == "ц":
                lastword = lastword[:-2] + "ты"
            elif lastword[-1] == "к":
                lastword = lastword.replace("о", "а") + "авы"

            elif lastword[-2] == "ч" or lastword[-1] == "ч":
                if lastword[-2] == "ч":
                    lastword = lastword[:-1] + "ны"
                if lastword[-1] == "ч":
                    lastword = lastword + "ны"

            elif lastword[-1] == "н" or lastword[-2] == "н":
                lastword = lastword[: lastword.rfind("н") + 1] + "ны"
            elif lastword[-1] == "д" or lastword[-2] == "д":
                lastword = lastword[: lastword.rfind("д") + 1] + "ны"

        if gender == "f":
            if lastword[-2:] in [
                "ці",
            ]:
                lastword = lastword[:-2] + "цяя"
            else:
                lastword = lastword[:-1] + "ая"

        if gender == "n":
            if lastword[-2:] in [
                "ці", "ца"
            ]:
                lastword = lastword[:-2] + "цяе"
            else:
                lastword = lastword[:-1] + "ае"

        outwords[-1] = self.title(lastword)
        if len(outwords) == 2 and "адна" in outwords[-2]:
            outwords[-2] = outwords[-1]
            del outwords[-1]

        if len(outwords) > 2 and "тысяч" in outwords[-1]:
            if 'сорак' in outwords[-3]:
                outwords[-3] = outwords[-3].replace('сорак', 'сарака')
            outwords[-3] = outwords[-3] + outwords[-2] + outwords[-1]
            del outwords[-1]
            del outwords[-1]

        elif len(outwords) > 1 and "тысяч" in outwords[-1]:
            outwords[-2] = outwords[-2] + outwords[-1]
            del outwords[-1]
        return " ".join(outwords).strip()

    def _money_verbose(self, number, currency):
        gender = "m"
        if currency == "UAH":
            gender = "f"

        return self._int2word(number, gender)

    def _cents_verbose(self, number, currency):
        if currency in ("UAH", "RUB", "BYN"):
            gender = "f"
        else:
            gender = "m"

        return self._int2word(number, gender)

    def _int2word(self, n, gender="m"):
        if isinstance(gender, bool) and gender:
            gender = "f"
        if n < 0:
            return " ".join([self.negword, self._int2word(abs(n), gender)])

        if n == 0:
            return ZERO

        words = []
        chunks = list(splitbyx(str(n), 3))
        i = len(chunks)
        for x in chunks:
            i -= 1

            if x == 0:
                continue

            n1, n2, n3 = get_digits(x)

            if n3 > 0:
                words.append(HUNDREDS[n3])

            if n2 > 1:
                words.append(TWENTIES[n2])

            if n2 == 1:
                words.append(TENS[n1])
            elif n1 > 0:
                if i == 0:
                    ones = ONES[gender]
                elif i == 1:
                    ones = ONES["f"]  # Thousands are feminine
                else:
                    ones = ONES["m"]

                words.append(ones[n1])

            if i > 0:
                words.append(self.pluralize(x, THOUSANDS[i]))

        return " ".join(words)
