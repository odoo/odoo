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

from .base import Num2Word_Base
from .utils import get_digits, splitbyx

GENDER_PLURAL_INDEXES = {
    'm': 0, 'masculine': 0, 'м': 0, 'мужской': 0,
    'f': 1, 'feminine': 1, 'ж': 0, 'женский': 0,
    'n': 2, 'neuter': 2, 'с': 0, 'средний': 0,
    'p': 3, 'plural': 3
}
CASE_INDEXES = {
    'n': 0, 'nominative': 0, 'и': 0, 'именительный': 0,
    'g': 1, 'genitive': 1, 'р': 1, 'родительный': 1,
    'd': 2, 'dative': 2, 'д': 2, 'дательный': 2,
    'a': 3, 'accusative': 3, 'в': 3, 'винительный': 3,
    'i': 4, 'instrumental': 4, 'т': 4, 'творительный': 4,
    'p': 5, 'prepositional': 5, 'п': 5, 'предложный': 5
}
# Default values
D_CASE = 'n'
D_PLURAL = False
D_GENDER = 'm'
D_ANIMATE = True


def get_num_element(cases_dict, num, **kwargs):
    return case_classifier_element(cases_dict[num], **kwargs)


def case_classifier_element(classifier, case=D_CASE, plural=D_PLURAL,
                            gender=D_GENDER, animate=D_ANIMATE):
    case = classifier[CASE_INDEXES[case]]
    if isinstance(case, str):
        return case

    if plural:
        gender = case[GENDER_PLURAL_INDEXES['plural']]
    else:
        gender = case[GENDER_PLURAL_INDEXES[gender]]
    if isinstance(gender, str):
        return gender

    if animate:
        return gender[0]
    return gender[1]


# format:
# {n : [case_1 .. case_5]}
# case: text or [gender_1 .. gender_3 plural_4]
# gender: text or [animate, inanimate]
ONES = {
    0: ['ноль', 'ноля', 'нолю', 'ноль', 'нолём', 'ноле'],
    1: [['один', 'одна', 'одно', 'одни'],
        ['одного', 'одной', 'одного', 'одних'],
        ['одному', 'одной', 'одному', 'одним'],
        [['одного', 'один'], 'одну', 'одно', ['одних', 'одни']],
        ['одним', 'одной', 'одним', 'одними'],
        ['одном', 'одной', 'одном', 'одних']],
    2: [['два', 'две', 'два', 'двое'],
        ['двух'] * 3 + ['двоих'],
        ['двум'] * 3 + ['двоим'],
        [['двух', 'два'], ['двух', 'две'], 'два', 'двоих'],
        ['двумя'] * 3 + ['двоими'],
        ['двух'] * 3 + ['двоих']],
    3: [['три'] * 3 + ['трое'],
        ['трёх'] * 3 + ['троих'],
        ['трём'] * 3 + ['троим'],
        [['трёх', 'три'], ['трёх', 'три'], 'три', 'троих'],
        ['тремя'] * 3 + ['троими'],
        ['трёх'] * 3 + ['троих']],
    4: [['четыре'] * 3 + ['четверо'],
        ['четырёх'] * 3 + ['четверых'],
        ['четырём'] * 3 + ['четверым'],
        [['четырёх', 'четыре'], ['четырёх', 'четыре'], 'четыре', 'четверых'],
        ['четырьмя'] * 3 + ['четверыми'],
        ['четырёх'] * 3 + ['четверых']],
    5: ['пять', 'пяти', 'пяти', 'пять', 'пятью', 'пяти'],
    6: ['шесть', 'шести', 'шести', 'шесть', 'шестью', 'шести'],
    7: ['семь', 'семи', 'семи', 'семь', 'семью', 'семи'],
    8: ['восемь', 'восьми', 'восьми', 'восемь', 'восемью', 'восьми'],
    9: ['девять', 'девяти', 'девяти', 'девять', 'девятью', 'девяти']
}

ONES_ORD_PREFIXES = {0: 'нулев', 1: 'перв', 2: 'втор', 4: 'четвёрт', 5: 'пят',
                     6: 'шест', 7: 'седьм', 8: 'восьм', 9: 'девят'}
ONES_ORD_POSTFIXES_GROUPS = {0: 0, 1: 1, 2: 0, 4: 1, 5: 1, 6: 0, 7: 0, 8: 0,
                             9: 1}
CASE_POSTFIXES = [[{0: 'ой', 1: 'ый'}, 'ая', 'ое', 'ые'],
                  ['ого', 'ой', 'ого', 'ых'],
                  ['ому', 'ой', 'ому', 'ым'],
                  [['ого', {0: 'ой', 1: 'ый'}], 'ую', 'ое', ['ых', 'ые']],
                  ['ым', 'ой', 'ым', 'ыми'],
                  ['ом', 'ой', 'ом', 'ых']]


def get_cases(prefix, post_group):
    return [[
        prefix + postfix if isinstance(postfix, str) else
        [prefix + animate if isinstance(animate, str) else
         prefix + animate[post_group]
         for animate in postfix] if isinstance(postfix, list) else
        prefix + postfix[post_group]
        for postfix in case]
        for case in CASE_POSTFIXES]


def get_ord_classifier(prefixes, post_groups):
    if isinstance(post_groups, int):
        post_groups = {n: post_groups for n, i in prefixes.items()}
    return {
        num: get_cases(prefix, post_groups[num])
        for num, prefix in prefixes.items()
    }


ONES_ORD = {
    3: [['третий', 'третья', 'третье', 'третьи'],
        ['третьего', 'третьей', 'третьего', 'третьих'],
        ['третьему', 'третьей', 'третьему', 'третьим'],
        [['третьего', 'третий'], 'третью', 'третье', ['третьих', 'третьи']],
        ['третьим', 'третьей', 'третьим', 'третьими'],
        ['третьем', 'третьей', 'третьем', 'третьих']],
}
ONES_ORD.update(
    get_ord_classifier(ONES_ORD_PREFIXES, ONES_ORD_POSTFIXES_GROUPS)
)

TENS_PREFIXES = {1: 'один', 2: 'две', 3: 'три', 4: 'четыр', 5: 'пят',
                 6: 'шест', 7: 'сем', 8: 'восем', 9: 'девят'}
TENS_POSTFIXES = ['надцать', 'надцати', 'надцати', 'надцать', 'надцатью',
                  'надцати']
TENS = {0: ['десять', 'десяти', 'десяти', 'десять', 'десятью', 'десяти']}
TENS.update({
    num: [prefix + postfix for postfix in TENS_POSTFIXES]
    for num, prefix in TENS_PREFIXES.items()
})

TENS_ORD_PREFIXES = {0: "десят"}
TENS_ORD_PREFIXES.update({
    num: prefix + 'надцат' for num, prefix in TENS_PREFIXES.items()
})
TENS_ORD = get_ord_classifier(TENS_ORD_PREFIXES, 1)

TWENTIES = {
    2: ['двадцать', 'двадцати', 'двадцати', 'двадцать', 'двадцатью',
        'двадцати'],
    3: ['тридцать', 'тридцати', 'тридцати', 'тридцать', 'тридцатью',
        'тридцати'],
    4: ['сорок', 'сорока', 'сорока', 'сорок', 'сорока', 'сорока'],
    5: ['пятьдесят', 'пятидесяти', 'пятидесяти', 'пятьдесят', 'пятьюдесятью',
        'пятидесяти'],
    6: ['шестьдесят', 'шестидесяти', 'шестидесяти', 'шестьдесят',
        'шестьюдесятью', 'шестидесяти'],
    7: ['семьдесят', 'семидесяти', 'семидесяти', 'семьдесят', 'семьюдесятью',
        'семидесяти'],
    8: ['восемьдесят', 'восьмидесяти', 'восьмидесяти', 'восемьдесят',
        'восемьюдесятью', 'восьмидесяти'],
    9: ['девяносто', 'девяноста', 'девяноста', 'девяносто', 'девяноста',
        'девяноста'],
}

TWENTIES_ORD_PREFIXES = {2: 'двадцат', 3: 'тридцат', 4: 'сороков',
                         5: 'пятидесят', 6: 'шестидесят', 7: 'семидесят',
                         8: 'восьмидесят', 9: 'девяност'}
TWENTIES_ORD_POSTFIXES_GROUPS = {2: 1, 3: 1, 4: 0, 5: 1, 6: 1, 7: 1, 8: 1,
                                 9: 1}
TWENTIES_ORD = get_ord_classifier(TWENTIES_ORD_PREFIXES,
                                  TWENTIES_ORD_POSTFIXES_GROUPS)

HUNDREDS = {
    1: ['сто', 'ста', 'ста', 'сто', 'ста', 'ста'],
    2: ['двести', 'двухсот', 'двумстам', 'двести', 'двумястами', 'двухстах'],
    3: ['триста', 'трёхсот', 'трёмстам', 'триста', 'тремястами', 'трёхстах'],
    4: ['четыреста', 'четырёхсот', 'четырёмстам', 'четыреста', 'четырьмястами',
        'четырёхстах'],
    5: ['пятьсот', 'пятисот', 'пятистам', 'пятьсот', 'пятьюстами', 'пятистах'],
    6: ['шестьсот', 'шестисот', 'шестистам', 'шестьсот', 'шестьюстами',
        'шестистах'],
    7: ['семьсот', 'семисот', 'семистам', 'семьсот', 'семьюстами', 'семистах'],
    8: ['восемьсот', 'восьмисот', 'восьмистам', 'восемьсот', 'восемьюстами',
        'восьмистах'],
    9: ['девятьсот', 'девятисот', 'девятистам', 'девятьсот', 'девятьюстами',
        'девятистах'],
}

HUNDREDS_ORD_PREFIXES = {
    num: case[1] if num != 1 else 'сот' for num, case in HUNDREDS.items()
}
HUNDREDS_ORD = get_ord_classifier(HUNDREDS_ORD_PREFIXES, 1)


THOUSANDS_PREFIXES = {2: 'миллион', 3: 'миллиард', 4: 'триллион',
                      5: 'квадриллион', 6: 'квинтиллион', 7: 'секстиллион',
                      8: 'септиллион', 9: 'октиллион', 10: 'нониллион'}
THOUSANDS_POSTFIXES = [('', 'а', 'ов'),
                       ('а', 'ов', 'ов'),
                       ('у', 'ам', 'ам'),
                       ('', 'а', 'ов'),
                       ('ом', 'ами', 'ами'),
                       ('е', 'ах', 'ах')]
THOUSANDS = {
    1: [['тысяча', 'тысячи', 'тысяч'],
        ['тысячи', 'тысяч', 'тысяч'],
        ['тысяче', 'тысячам', 'тысячам'],
        ['тысячу', 'тысячи', 'тысяч'],
        ['тысячей', 'тысячами', 'тысячами'],
        ['тысяче', 'тысячах', 'тысячах']]
}
THOUSANDS.update({
    num: [
        [prefix + postfix for postfix in case] for case in THOUSANDS_POSTFIXES
    ] for num, prefix in THOUSANDS_PREFIXES.items()
})


def get_thousands_elements(num, case):
    return THOUSANDS[num][CASE_INDEXES[case]]


THOUSANDS_ORD_PREFIXES = {1: 'тысячн'}
THOUSANDS_ORD_PREFIXES.update({
    num: prefix + 'н' for num, prefix in THOUSANDS_PREFIXES.items()
})
THOUSANDS_ORD = get_ord_classifier(THOUSANDS_ORD_PREFIXES, 1)


class Num2Word_RU(Num2Word_Base):
    CURRENCY_FORMS = {
        'RUB': (
            ('рубль', 'рубля', 'рублей'), ('копейка', 'копейки', 'копеек')
        ),
        'EUR': (
            ('евро', 'евро', 'евро'), ('цент', 'цента', 'центов')
        ),
        'USD': (
            ('доллар', 'доллара', 'долларов'), ('цент', 'цента', 'центов')
        ),
        'UAH': (
            ('гривна', 'гривны', 'гривен'), ('копейка', 'копейки', 'копеек')
        ),
        'KZT': (
            ('тенге', 'тенге', 'тенге'), ('тиын', 'тиына', 'тиынов')
        ),
        'BYN': (
            ('белорусский рубль', 'белорусских рубля', 'белорусских рублей'),
            ('копейка', 'копейки', 'копеек')
        ),
        'UZS': (
            ('сум', 'сума', 'сумов'), ('тийин', 'тийина', 'тийинов')
        ),
        'PLN': (
            ('польский злотый', 'польских слотых', 'польских злотых'),
            ('грош', 'гроша', 'грошей')
        ),
    }

    def setup(self):
        self.negword = "минус"
        self.pointword = ('целая', 'целых', 'целых')
        self.pointword_ord = get_cases("цел", 1)

    def to_cardinal(self, number, case=D_CASE, plural=D_PLURAL,
                    gender=D_GENDER, animate=D_ANIMATE):
        n = str(number).replace(',', '.')
        if '.' in n:
            left, right = n.split('.')
            decimal_part = self._int2word(int(right), cardinal=True,
                                          gender='f')
            return u'%s %s %s %s' % (
                self._int2word(int(left), cardinal=True, gender='f'),
                self.pluralize(int(left), self.pointword),
                decimal_part,
                self.__decimal_bitness(right)
            )
        else:
            return self._int2word(int(n), cardinal=True, case=case,
                                  plural=plural, gender=gender,
                                  animate=animate)

    def __decimal_bitness(self, n):
        if n[-1] == "1" and n[-2:] != "11":
            return self._int2word(10 ** len(n), cardinal=False, gender='f')
        return self._int2word(10 ** len(n), cardinal=False, case='g',
                              plural=True)

    def pluralize(self, n, forms):
        if n % 100 in (11, 12, 13, 14):
            return forms[2]
        if n % 10 == 1:
            return forms[0]
        if n % 10 in (2, 3, 4):
            return forms[1]
        return forms[2]

    def to_ordinal(self, number, case=D_CASE, plural=D_PLURAL, gender=D_GENDER,
                   animate=D_ANIMATE):
        self.verify_ordinal(number)
        n = str(number).replace(',', '.')
        return self._int2word(int(n), cardinal=False, case=case, plural=plural,
                              gender=gender, animate=animate)

    def _money_verbose(self, number, currency):
        if currency == 'UAH':
            return self._int2word(number, gender='f')
        return self._int2word(number, gender='m')

    def _cents_verbose(self, number, currency):
        if currency in ('UAH', 'RUB', 'BYN'):
            return self._int2word(number, gender='f')
        return self._int2word(number, gender='m')

    def _int2word(self, n, feminine=False, cardinal=True, case=D_CASE,
                  plural=D_PLURAL, gender=D_GENDER, animate=D_ANIMATE):
        """
        n: number
        feminine: not used - for backward compatibility
        cardinal:True - cardinal
                False - ordinal
        case:   'n' - nominative
                'g' - genitive
                'd' - dative
                'a' - accusative
                'i' - instrumental
                'p' - prepositional
        plural: True - plural
                False - singular
        gender: 'f' - masculine
                'm' - feminine
                'n' - neuter
        animate: True - animate
                 False - inanimate
        """
        # For backward compatibility
        if feminine:
            gender = 'f'

        kwargs = {'case': case, 'plural': plural, 'gender': gender,
                  'animate': animate}

        if n < 0:
            return ' '.join([self.negword, self._int2word(abs(n),
                                                          cardinal=cardinal,
                                                          **kwargs)])

        if n == 0:
            return get_num_element(ONES, 0, **kwargs) if cardinal else \
                   get_num_element(ONES_ORD, 0, **kwargs)

        words = []
        chunks = list(splitbyx(str(n), 3))
        ord_join = chunks[-1] == 0  # join in one word if ending on 'тысячный'
        i = len(chunks)
        rightest_nonzero_chunk_i = i - 1 - max(
            [i for i, e in enumerate(chunks) if e != 0])
        for x in chunks:
            chunk_words = []
            i -= 1

            if x == 0:
                continue

            n1, n2, n3 = get_digits(x)

            if cardinal:
                chunk_words.extend(
                    self.__chunk_cardianl(n3, n2, n1, i, **kwargs)
                )
                if i > 0:
                    chunk_words.append(
                        self.pluralize(x, get_thousands_elements(i, case)))
            # ordinal, not joined like 'двухтысячный'
            elif not (ord_join and rightest_nonzero_chunk_i == i):
                chunk_words.extend(
                    self.__chunk_ordinal(n3, n2, n1, i, **kwargs)
                )
                if i > 0:
                    t_case = case if rightest_nonzero_chunk_i == i else 'n'
                    chunk_words.append(
                        self.pluralize(x, get_thousands_elements(i, t_case)))
            # ordinal, joined
            else:
                chunk_words.extend(
                    self.__chunk_ordinal_join(n3, n2, n1, i, **kwargs)
                )
                if i > 0:
                    chunk_words.append(
                        get_num_element(THOUSANDS_ORD, i, **kwargs))

                chunk_words = [''.join(chunk_words)]

            words.extend(chunk_words)

        return ' '.join(words)

    def __chunk_cardianl(self, hundreds, tens, ones, chunk_num, **kwargs):
        words = []
        if hundreds > 0:
            words.append(get_num_element(HUNDREDS, hundreds, **kwargs))

        if tens > 1:
            words.append(get_num_element(TWENTIES, tens, **kwargs))

        if tens == 1:
            words.append(get_num_element(TENS, ones, **kwargs))
        elif ones > 0:
            if chunk_num == 0:
                w_ones = get_num_element(ONES, ones, **kwargs)
            elif chunk_num == 1:
                # Thousands are feminine
                f_kwargs = kwargs.copy()
                f_kwargs['gender'] = 'f'
                w_ones = get_num_element(ONES, ones, **f_kwargs)
            else:
                w_ones = get_num_element(ONES, ones, **kwargs)

            words.append(w_ones)
        return words

    def __chunk_ordinal(self, hundreds, tens, ones, chunk_num, **kwargs):
        words = []
        if hundreds > 0:
            if tens == 0 and ones == 0:
                words.append(get_num_element(HUNDREDS_ORD, hundreds, **kwargs))
            else:
                words.append(get_num_element(HUNDREDS, hundreds))

        if tens > 1:
            if ones == 0:
                words.append(get_num_element(TWENTIES_ORD, tens, **kwargs))
            else:
                words.append(get_num_element(TWENTIES, tens))

        if tens == 1:
            words.append(get_num_element(TENS_ORD, ones, **kwargs))
        elif ones > 0:
            if chunk_num == 0:
                w_ones = get_num_element(ONES_ORD, ones, **kwargs)
            # тысячный, миллионнный и т.д.
            elif chunk_num > 0 and ones == 1 and hundreds == 0 and tens == 0:
                w_ones = None
            elif chunk_num == 1:
                # Thousands are feminine
                w_ones = get_num_element(ONES, ones, gender='f')
            else:
                w_ones = get_num_element(ONES, ones)

            if w_ones:
                words.append(w_ones)

        return words

    def __chunk_ordinal_join(self, hundreds, tens, ones, chunk_num, **kwargs):
        words = []

        if hundreds > 1:
            words.append(get_num_element(HUNDREDS, hundreds, case='g'))
        elif hundreds == 1:
            words.append(get_num_element(HUNDREDS, hundreds))   # стО, not стА

        if tens == 9:
            words.append(get_num_element(TWENTIES, tens))   # девяностО, not А
        elif tens > 1:
            words.append(get_num_element(TWENTIES, tens, case='g'))

        if tens == 1:
            words.append(get_num_element(TENS, ones, case='g'))
        elif ones > 0:
            if chunk_num == 0:
                w_ones = get_num_element(ONES_ORD, ones, **kwargs)
            # тысячный, миллионнный и т.д., двадцатиодномиллионный
            elif chunk_num > 0 and ones == 1 and tens != 1:
                if tens == 0 and hundreds == 0:
                    w_ones = None
                else:
                    w_ones = get_num_element(ONES, 1, gender='n')
            else:
                w_ones = get_num_element(ONES, ones, case='g')

            if w_ones:
                words.append(w_ones)

        return words
