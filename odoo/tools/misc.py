import collections
import typing
from difflib import HtmlDiff

from odoo.libs import xml as _xml_lib
from odoo.libs.collections import (
    Collector,
    ConstantMapping,
    LastOrderedSet,
    OrderedSet,
    ReadonlyDict,
    ReversedIterable,
    StackMap,
    frozendict,
    submap,
)
from odoo.libs.func import Callbacks
from odoo.libs.iteration import (
    PENDING,
    SENTINEL,
    Sentinel,
    groupby,
    merge_sequences,
    partition,
    topological_sort,
    unique,
)
from odoo.libs.locale import posix_to_ldml
from odoo.libs.logging import (
    lower_logging,
    mute_logger,
    unquote,
)
from odoo.libs.text import (
    get_flag,
    html_escape,
    human_size,
    is_encodable,
    mod10r,
    remove_accents,
    str2bool,
    street_split,
)
from odoo.libs.utils import (
    discardattr,
    format_frame,
    has_list_types,
    is_list_of,
    replace_exceptions,
)

from .files import (
    file_open,
    file_open_temporary_directory,
    file_path,
)
from .formatting import (
    DATE_LENGTH,
    DATETIME_FORMATS_MAP,
    DEFAULT_SERVER_DATE_FORMAT,
    DEFAULT_SERVER_DATETIME_FORMAT,
    DEFAULT_SERVER_TIME_FORMAT,
    NEGATIVE_SIGN_JOINER,
    NON_BREAKING_SPACE,
    _format_time_ago,
    format_amount,
    format_amount_parts,
    format_date,
    format_datetime,
    format_decimalized_amount,
    format_decimalized_number,
    format_duration,
    format_time,
    formatLang,
    parse_date,
)
from .locale_utils import (
    babel_locale_parse,
    get_iso_codes,
    get_lang,
    get_languages,
)
from .security import (
    consteq,
    hash_sign,
    hmac,
    is_valid_limited_field_access_token,
    limited_field_access_token,
    resolve_hash_signed,
)
from .subprocess import (
    dumpstacks,
    exec_pg_environ,
    get_executable_path,
    get_pg_tool_path,
    real_time,
    stripped_sys_argv,
)

if typing.TYPE_CHECKING:
    from collections.abc import Callable

__all__ = [
    "DATETIME_FORMATS_MAP",
    "DATE_LENGTH",
    "DEFAULT_SERVER_DATETIME_FORMAT",
    "DEFAULT_SERVER_DATE_FORMAT",
    "DEFAULT_SERVER_TIME_FORMAT",
    "NEGATIVE_SIGN_JOINER",
    "NON_BREAKING_SPACE",
    "PENDING",
    "SENTINEL",
    "SKIPPED_ELEMENT_TYPES",
    "Callbacks",
    "Collector",
    "ConstantMapping",
    "LastOrderedSet",
    "OrderedSet",
    "ReadonlyDict",
    "ReversedIterable",
    "Sentinel",
    "StackMap",
    "babel_locale_parse",
    "clean_context",
    "consteq",
    "discardattr",
    "dumpstacks",
    "exec_pg_environ",
    "file_open",
    "file_open_temporary_directory",
    "file_path",
    "formatLang",
    "format_amount",
    "format_amount_parts",
    "format_date",
    "format_datetime",
    "format_decimalized_amount",
    "format_decimalized_number",
    "format_duration",
    "format_frame",
    "format_time",
    "frozendict",
    "get_diff",
    "get_executable_path",
    "get_flag",
    "get_iso_codes",
    "get_lang",
    "get_languages",
    "get_pg_tool_path",
    "groupby",
    "has_list_types",
    "hash_sign",
    "hmac",
    "html_escape",
    "human_size",
    "is_encodable",
    "is_list_of",
    "is_valid_limited_field_access_token",
    "limited_field_access_token",
    "lower_logging",
    "merge_sequences",
    "mod10r",
    "mute_logger",
    "parse_date",
    "partition",
    "posix_to_ldml",
    "real_time",
    "remove_accents",
    "replace_exceptions",
    "resolve_hash_signed",
    "str2bool",
    "street_split",
    "stripped_sys_argv",
    "submap",
    "topological_sort",
    "unique",
    "unquote",
]

SKIPPED_ELEMENT_TYPES = _xml_lib.SKIPPED_ELEMENT_TYPES


def clean_context(context: dict[str, typing.Any]) -> dict[str, typing.Any]:
    return {k: v for k, v in context.items() if not k.startswith("default_")}


def get_diff(
    data_from: tuple[str, str],
    data_to: tuple[str, str],
    custom_style: str | None = None,
    dark_color_scheme: bool = False,
) -> str:
    def style_html_diff(
        html_diff: str, custom_style: str | None, dark_color_scheme: bool
    ) -> str:
        to_append = {
            'class="diff_header"': "bg-600 text-light text-center align-top px-2",
            'class="diff_next"': "d-none",
        }
        for attribute, classes in to_append.items():
            html_diff = html_diff.replace(
                f" {attribute}", ' %s %s"' % (attribute[:-1], classes)
            )
        html_diff = html_diff.replace(' nowrap="nowrap"', "")
        colors = (
            ("#7f2d2f", "#406a2d", "#51232f", "#3f483b")
            if dark_color_scheme
            else ("#ffc1c0", "#abf2bc", "#ffebe9", "#e6ffec")
        )
        html_diff += (
            custom_style
            or """
            <style>
                .modal-dialog.modal-lg:has(table.diff) {
                    max-width: 1600px;
                    padding-left: 1.75rem;
                    padding-right: 1.75rem;
                }
                table.diff { width: 100%%; }
                table.diff th.diff_header { width: 50%%; }
                table.diff td.diff_header { white-space: nowrap; }
                table.diff td.diff_header + td { width: 50%%; }
                table.diff td { word-break: break-all; vertical-align: top; }
                table.diff .diff_chg, table.diff .diff_sub, table.diff .diff_add {
                    display: inline-block;
                    color: inherit;
                }
                table.diff .diff_sub, table.diff td:nth-child(3) > .diff_chg { background-color: %s }
                table.diff .diff_add, table.diff td:nth-child(6) > .diff_chg { background-color: %s }
                table.diff td:nth-child(3):has(>.diff_chg, .diff_sub) { background-color: %s }
                table.diff td:nth-child(6):has(>.diff_chg, .diff_add) { background-color: %s }
            </style>
        """
            % colors
        )
        return html_diff

    diff = HtmlDiff(tabsize=2).make_table(
        data_from[0].splitlines(),
        data_to[0].splitlines(),
        data_from[1],
        data_to[1],
        context=True,
        numlines=3,
    )
    return style_html_diff(diff, custom_style, dark_color_scheme)
