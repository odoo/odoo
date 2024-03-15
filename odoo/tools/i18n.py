from __future__ import annotations

from typing import TYPE_CHECKING, Literal, Optional, Sequence

from babel import lists

from odoo.tools.misc import babel_locale_parse, get_lang

if TYPE_CHECKING:
    import odoo.api


def format_list(
    env: odoo.api.Environment,
    lst: Sequence[str],
    style: Literal["standard", "standard-short", "or", "or-short", "unit", "unit-short", "unit-narrow"] = "standard",
    lang_code: Optional[str] = None,
) -> str:
    """
    Format the items in `lst` as a list in a locale-dependent manner with the chosen style.

    The available styles are defined by babel according to the Unicode TR35-49 spec:
    * standard:
      A typical 'and' list for arbitrary placeholders.
      e.g. "January, February, and March"
    * standard-short:
      A short version of an 'and' list, suitable for use with short or abbreviated placeholder values.
      e.g. "Jan., Feb., and Mar."
    * or:
      A typical 'or' list for arbitrary placeholders.
      e.g. "January, February, or March"
    * or-short:
      A short version of an 'or' list.
      e.g. "Jan., Feb., or Mar."
    * unit:
      A list suitable for wide units.
      e.g. "3 feet, 7 inches"
    * unit-short:
      A list suitable for short units
      e.g. "3 ft, 7 in"
    * unit-narrow:
      A list suitable for narrow units, where space on the screen is very limited.
      e.g. "3′ 7″"

    See https://www.unicode.org/reports/tr35/tr35-49/tr35-general.html#ListPatterns for more details.

    :param env: the current environment.
    :param lst: the sequence of items to format into a list.
    :param style: the style to format the list with.
    :param lang_code: the locale (i.e. en_US).
    :return: the formatted list.
    """
    locale = babel_locale_parse(lang_code or get_lang(env).code)
    # Some styles could be unavailable for the chosen locale
    if style not in locale.list_patterns:
        style = "standard"
    return lists.format_list(lst, style, locale)
