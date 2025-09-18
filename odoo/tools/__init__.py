# Odoo-dependent tools (remain in tools/)
# Re-export additional utilities from libs/ not covered by misc.py
# Note: misc.py already re-exports collections, iteration, text, utils from libs/
from odoo.libs import constants
from odoo.libs.func import (
    classproperty,
    conditional,
    lazy,
    lazy_classproperty,
    reset_cached_properties,
)
from odoo.libs.numbers.float_utils import (
    float_compare,
    float_is_zero,
    float_repr,
    float_round,
    float_split,
    float_split_str,
)
from odoo.libs.parse_version import parse_version
from odoo.libs.set_expression import SetDefinitions
from odoo.libs.web import urls

from .cache import ormcache, ormcache_context
from .config import config
from .convert import (
    convert_csv_import,
    convert_file,
    convert_sql_import,
    convert_xml_import,
)
from .i18n import format_list, py_to_js_locale
from .json import json_default
from .mail import (
    email_domain_extract,
    email_domain_normalize,
    email_normalize,
    email_normalize_all,
    email_split,
    encapsulate_email,
    formataddr,
    html2plaintext,
    html_escape,
    html_normalize,
    html_sanitize,
    is_html_empty,
    parse_contact_from_email,
    plaintext2html,
    single_email_re,
)
from .misc import (
    DEFAULT_SERVER_DATETIME_FORMAT,
    DEFAULT_SERVER_DATE_FORMAT,
    DEFAULT_SERVER_TIME_FORMAT,
    NON_BREAKING_SPACE,
    SKIPPED_ELEMENT_TYPES,
    DotDict,
    LastOrderedSet,
    OrderedSet,
    Reverse,
    babel_locale_parse,
    clean_context,
    consteq,
    discardattr,
    file_open,
    file_open_temporary_directory,
    file_path,
    find_in_path,
    formatLang,
    format_amount,
    format_date,
    format_datetime,
    format_duration,
    format_time,
    frozendict,
    get_iso_codes,
    get_lang,
    groupby,
    hash_sign,
    hmac,
    human_size,
    is_list_of,
    merge_sequences,
    mod10r,
    mute_logger,
    parse_date,
    partition,
    posix_to_ldml,
    real_time,
    remove_accents,
    replace_exceptions,
    reverse_enumerate,
    split_every,
    str2bool,
    street_split,
    topological_sort,
    unique,
    verify_hash_signed,
)
from .query import Query
from .sql import (
    SQL,
    create_index,
    drop_view_if_exists,
    escape_psql,
    index_exists,
    make_identifier,
    make_index_name,
    pattern_to_translated_trigram_pattern,
    pg_varchar,
    reverse_order,
    value_to_translated_trigram_pattern,
)
from .translate import LazyTranslate, _, html_translate, xml_translate
from .xml_utils import (
    cleanup_xml_node,
    load_xsd_files_from_url,
    validate_xml_from_attachment,
)
