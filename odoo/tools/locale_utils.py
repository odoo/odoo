import csv
import functools
import logging
import typing
from operator import itemgetter

import babel

from odoo.libs.debug_log import DebugLog

from .files import file_open

if typing.TYPE_CHECKING:
    from odoo.api import Environment

    from odoo.addons.base.models.res_lang import LangData
else:
    Environment = typing.Any
    LangData = typing.Any

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


def get_iso_codes(lang: str) -> str:
    if lang.find("_") != -1:
        lang_items = lang.split("_")
        if lang_items[0] == lang_items[1].lower():
            lang = lang_items[0]
    return lang


@functools.cache
def _read_lang_csv() -> tuple[tuple[str, str], ...]:
    with file_open("base/data/res.lang.csv") as csvfile:
        reader = csv.reader(csvfile, delimiter=",", quotechar='"')
        fields = next(reader)
        code_index = fields.index("code")
        name_index = fields.index("name")
        result = [(row[code_index], row[name_index]) for row in reader]

    return tuple(sorted(result or [("en_US", "English")], key=itemgetter(1)))


def get_languages() -> list[tuple[str, str]]:
    try:
        return list(_read_lang_csv())
    except Exception as exc:
        _logger.exception("Could not read res.lang.csv")
        _debug.logic("locale.lang_csv_unreadable", error=type(exc).__name__)
        return [("en_US", "English")]


def _company_lang(env: Environment) -> str | None:
    if "res.users" not in env.registry:
        return None
    try:
        return env.user.with_context(lang="en_US").company_id.partner_id.lang
    except AttributeError:
        # a DB-free registry whose user or company stub carries no partner
        return None


def get_lang(env: Environment, lang_code: str | None = None) -> LangData:
    locale = env.registry.locale
    langs = locale.installed_langs(env)
    lang = "en_US" if "en_US" in langs else langs[0]
    source = "default"  # debuglog
    if lang_code and lang_code in langs:
        lang = lang_code
        source = "argument"  # debuglog
    elif (context_lang := env.context.get("lang")) in langs:
        lang = context_lang
        source = "context"  # debuglog
    elif (company_lang := _company_lang(env)) in langs:
        lang = company_lang
        source = "company"  # debuglog
    _debug.logic(
        "locale.lang_chosen",
        lang=lang,
        source=source,
        requested=lang_code,
        installed=len(langs),
    )
    return locale.lang_data(env, lang)


@functools.cache
def babel_locale_parse(lang_code: str | None) -> babel.Locale:
    if lang_code:
        try:
            return babel.Locale.parse(lang_code)
        except Exception:  # noqa: S110  an unknown lang_code falls through to Locale.default() below
            pass
    try:
        locale = babel.Locale.default()
        _debug.logic("locale.babel_defaulted", requested=lang_code, locale=str(locale))
        return locale
    except Exception:
        _debug.logic("locale.babel_fallback_en_US", requested=lang_code)
        return babel.Locale.parse("en_US")
