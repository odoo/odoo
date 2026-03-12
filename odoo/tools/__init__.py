# Part of Odoo. See LICENSE file for full copyright and licensing details.
# ruff: noqa: F401

from . import constants
from . import urls
from .parse_version import parse_version
from .binary import BinaryBytes, BinaryValue
from .config import config
from .float_utils import float_compare, float_is_zero, float_repr, float_round, float_split, float_split_str
from .func import classproperty, conditional, lazy, lazy_classproperty, reset_cached_properties
from .i18n import format_list, py_to_js_locale
from .json import json_default
from .mail import *
from .misc import *
from .sql import SQL, drop_view_if_exists
from .translate import _, html_translate, xml_translate, LazyTranslate
from .xml_utils import cleanup_xml_node, load_xsd_files_from_url, validate_xml_from_attachment
from .convert import convert_csv_import, convert_file, convert_sql_import, convert_xml_import
from .set_expression import SetDefinitions


def __getattr__(name):
    import warnings  # noqa: PLC0415
    if name in ('cache', 'ormcache'):
        warnings.warn("Since 20.0 import ormcache from odoo.api", DeprecationWarning, stacklevel=2)
        from odoo.orm import cache  # noqa: PLC0415
        return cache if name == 'cache' else cache.ormcache
    raise AttributeError(name=name)
