import logging
import re

from odoo import models

_logger = logging.getLogger(__name__)

text_type = str


# https://github.com/dchaplinsky/translit-ua/blob/master/translitua/translit.py


def convert_table(table):
    """
    >>> print(1072 in convert_table({"а": "a"}))
    True
    >>> print(1073 in convert_table({"а": "a"}))
    False
    >>> print(convert_table({"а": "a"})[1072] == "a")
    True
    >>> print(len(convert_table({"а": "a"}).keys()) == 1)
    True
    """

    return dict((ord(k), v) for k, v in table.items())


def add_uppercase(table):
    """
    Extend the table with uppercase options
    >>> print("а" in add_uppercase({"а": "a"}))
    True
    >>> print(add_uppercase({"а": "a"})["а"] == "a")
    True
    >>> print("А" in add_uppercase({"а": "a"}))
    True
    >>> print(add_uppercase({"а": "a"})["А"] == "A")
    True
    >>> print(len(add_uppercase({"а": "a"}).keys()))
    2
    >>> print("Аа" in add_uppercase({"аа": "aa"}))
    True
    >>> print(add_uppercase({"аа": "aa"})["Аа"] == "Aa")
    True
    """
    orig = table.copy()
    orig.update(
        dict((k.capitalize(), v.capitalize()) for k, v in table.items()))

    return orig


class UkrainianKMU:
    """
    According to National system from
    https://en.wikipedia.org/wiki/Romanization_of_Ukrainian#Tables_of_romanization_systems
    """
    _MAIN_TRANSLIT_TABLE = {
        u'а': u'a',
        u'б': u'b',
        u'в': u'v',
        u'г': u'h',
        u'ґ': u'g',
        u'д': u'd',
        u'е': u'e',
        u'є': u'ie',
        u'ж': u'zh',
        u'з': u'z',
        u'и': u'y',
        u'і': u'i',
        u'ї': u'i',
        u'й': u'i',
        u'к': u'k',
        u'л': u'l',
        u'м': u'm',
        u'н': u'n',
        u'о': u'o',
        u'п': u'p',
        u'р': u'r',
        u'с': u's',
        u'т': u't',
        u'у': u'u',
        u'ф': u'f',
        u'х': u'kh',
        u'ц': u'ts',
        u'ч': u'ch',
        u'ш': u'sh',
        u'щ': u'shch',
        u'ю': u'iu',
        u'я': u'ia',
        u'ь': u'\'',
        u'Ь': u'\'',

    }

    _DELETE_CASES = [
        # u'ь',
        # u'Ь',
        u'\u0027',
        u'\u2019',
        u'\u02BC',
    ]

    _SPECIAL_CASES = {
        u'зг': u'zgh',
        u'ЗГ': u'ZGh',
    }

    _FIRST_CHARACTERS = {
        u'є': u'ye',
        u'ї': u'yi',
        u'й': u'y',
        u'ю': u'yu',
        u'я': u'ya'
    }

    MAIN_TRANSLIT_TABLE = convert_table(add_uppercase(_MAIN_TRANSLIT_TABLE))
    FIRST_CHARACTERS = add_uppercase(_FIRST_CHARACTERS)
    SPECIAL_CASES = add_uppercase(_SPECIAL_CASES)

    PATTERN1 = re.compile(u'(?mu)' + u'|'.join(SPECIAL_CASES.keys()))
    PATTERN2 = re.compile(u'(?mu)' + r'\b(' +
                          u'|'.join(FIRST_CHARACTERS.keys()) + u')')
    DELETE_PATTERN = re.compile(u'(?mu)' + u'|'.join(_DELETE_CASES))


def translit(src, table=UkrainianKMU, preserve_case=True):
    u""" Transliterates given unicode `src` text
    to transliterated variant according to a given transliteration table.
    Official ukrainian transliteration is used by default
    :param src: string to transliterate
    :type src: str
    :param table: transliteration table
    :type table: transliteration table object
    :param preserve_case: convert result to uppercase if source is uppercased
    (see the example below for the difference that flag makes)
    :type preserve_case: bool
    :returns: transliterated string
    :rtype: str
    >>> print(translit(u"Дмитро Згуровский"))
    Dmytro Zghurovskyi
    >>> print(translit(u"Дмитро ЗГуровский"))
    Dmytro ZGhurovskyi
    >>> print(translit(u"Дмитро згуровский"))
    Dmytro zghurovskyi
    >>> print(translit(u"Євген Петренко"))
    Yevhen Petrenko
    >>> print(translit(u"Петренко Євген"))
    Petrenko Yevhen
    >>> print(translit(u"Петренко.Євген"))
    Petrenko.Yevhen
    >>> print(translit(u"Петренко,Євген"))
    Petrenko,Yevhen
    >>> print(translit(u"Петренко/Євген"))
    Petrenko/Yevhen
    >>> print(translit(u"Євгєн"))
    Yevhien
    >>> print(translit(u"Яготин"))
    Yahotyn
    >>> print(translit(u"Ярошенко"))
    Yaroshenko
    >>> print(translit(u"Костянтин"))
    Kostiantyn
    >>> print(translit(u"Знам'янка"))
    Znamianka
    >>> print(translit(u"Знам’янка"))
    Znamianka
    >>> print(translit(u"Знам’янка"))
    Znamianka
    >>> print(translit(u"Феодосія"))
    Feodosiia
    >>> print(translit(u"Ньютон"))
    Niuton
    >>> print(translit(u"піранья"))
    pirania
    >>> print(translit(u"кур'єр"))
    kurier
    >>> print(translit(u"ЗГУРОВСЬКИЙ"))
    ZGHUROVSKYI
    >>> print(translit(u"ЗГУРОВСЬКИЙ", preserve_case=False))
    ZGhUROVSKYI
    """

    src = text_type(src)
    src_is_upper = src.isupper()

    if hasattr(table, "DELETE_PATTERN"):
        src = table.DELETE_PATTERN.sub(u"", src)

    if hasattr(table, "PATTERN1"):
        src = table.PATTERN1.sub(lambda x: table.SPECIAL_CASES[x.group()], src)

    if hasattr(table, "PATTERN2"):
        src = table.PATTERN2.sub(lambda x: table.FIRST_CHARACTERS[x.group()],
                                 src)
    res = src.translate(table.MAIN_TRANSLIT_TABLE)

    if src_is_upper and preserve_case:
        return res.upper()
    return res


class TranslitUaMixin(models.AbstractModel):
    _name = 'kw.translit.ua.mixin'
    _description = 'Translit UA Mixin'

    @staticmethod
    def translitua(name, preserve_case=True):
        return translit(name, preserve_case=preserve_case)
