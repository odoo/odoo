# Part of Odoo. See LICENSE file for full copyright and licensing details.
# ruff: noqa:  E402, F401, F403

from . import constants
from .parse_version import parse_version
from .barcode import check_barcode_encoding
from .cache import ormcache, ormcache_context
from .config import config
from .date_utils import *
from .float_utils import *
from .func import *
from .i18n import format_list, py_to_js_locale
from .image import image_process
from .json import json_default

# Monkeypatch -- werkzeug_urls requires json_default
# and is needed by modules below, i.e. `mail.validate_url`
from odoo._monkeypatches import Monkeypatch
Monkeypatch.patch_module('werkzeug.urls')

from .mail import *
from .misc import *
from .query import Query
from .sql import *
from .translate import _, html_translate, xml_translate, LazyTranslate
from .xml_utils import cleanup_xml_node, load_xsd_files_from_url, validate_xml_from_attachment
from .convert import convert_csv_import, convert_file, convert_sql_import, convert_xml_import
from .js_transpiler import transpile_javascript, is_odoo_module, URL_RE, ODOO_MODULE_RE
from .sourcemap_generator import SourceMapGenerator
from .set_expression import SetDefinitions
