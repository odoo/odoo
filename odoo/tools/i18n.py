from typing import TYPE_CHECKING, Literal

from babel import lists

from odoo.tools.locale_utils import babel_locale_parse, get_lang

if TYPE_CHECKING:
    from collections.abc import Iterable

    import odoo.api


def format_list(
    env: odoo.api.Environment | None,
    lst: Iterable,
    style: Literal[
        "standard",
        "standard-short",
        "or",
        "or-short",
        "unit",
        "unit-short",
        "unit-narrow",
    ] = "standard",
    lang_code: str | None = None,
) -> str:
    locale = babel_locale_parse(
        lang_code or (get_lang(env).code if env is not None else "en_US")
    )
    items = [str(el) for el in lst]
    try:
        return lists.format_list(items, style, locale)
    except KeyError, ValueError:
        # an unknown style is a ValueError; a style the locale defines only in
        # part (es_MX `unit-short` has an `end` and no `start`) is a KeyError
        return lists.format_list(items, "standard", locale)
