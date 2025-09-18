"""
Language and locale utilities for Odoo.
"""

import csv
import logging
import typing
from operator import itemgetter

import babel

from .files import file_open

if typing.TYPE_CHECKING:
    from odoo.api import Environment

    from odoo.addons.base.models.res_lang import LangData

_logger = logging.getLogger(__name__)


def get_iso_codes(lang: str) -> str:
    if lang.find("_") != -1:
        lang_items = lang.split("_")
        if lang_items[0] == lang_items[1].lower():
            lang = lang_items[0]
    return lang


def scan_languages() -> list[tuple[str, str]]:
    """Returns all languages supported by Odoo for translation

    :returns: a list of (lang_code, lang_name) pairs
    :rtype: [(str, unicode)]
    """
    try:
        # read (code, name) from languages in base/data/res.lang.csv
        with file_open("base/data/res.lang.csv") as csvfile:
            reader = csv.reader(csvfile, delimiter=",", quotechar='"')
            fields = next(reader)
            code_index = fields.index("code")
            name_index = fields.index("name")
            result = [(row[code_index], row[name_index]) for row in reader]
    except Exception:
        _logger.error("Could not read res.lang.csv")
        result = []

    return sorted(result or [("en_US", "English")], key=itemgetter(1))


def get_lang(env: Environment, lang_code: str | None = None) -> LangData:
    """
    Retrieve the first lang object installed, by checking the parameter lang_code,
    the context and then the company. If no lang is installed from those variables,
    fallback on english or on the first lang installed in the system.

    :param env:
    :param str lang_code: the locale (i.e. en_US)
    :return LangData: the first lang found that is installed on the system.
    """
    langs = [code for code, _ in env["res.lang"].get_installed()]
    lang = "en_US" if "en_US" in langs else langs[0]
    if lang_code and lang_code in langs:
        lang = lang_code
    elif (context_lang := env.context.get("lang")) in langs:
        lang = context_lang
    elif (
        company_lang := env.user.with_context(lang="en_US").company_id.partner_id.lang
    ) in langs:
        lang = company_lang
    return env["res.lang"]._get_data(code=lang)


def babel_locale_parse(lang_code: str | None) -> babel.Locale:
    if lang_code:
        try:
            return babel.Locale.parse(lang_code)
        except Exception:
            pass
    try:
        return babel.Locale.default()
    except Exception:
        return babel.Locale.parse("en_US")
