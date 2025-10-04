# Part of Odoo. See LICENSE file for full copyright and licensing details.

import warnings
from odoo import http
from odoo.tools import lazy
from odoo.addons.web.controllers import (
    action, binary, database, dataset, export, home, report, session,
    utils, view, webclient,
)

_MOVED_TO_MAP = {
    '_get_login_redirect_url': utils,
    '_local_web_translations': webclient,
    'Action': action,
    'allow_empty_iterable': export,
    'Binary': binary,
    'clean': binary,
    'clean_action': utils,
    'content_disposition': http,
    'CONTENT_MAXAGE': webclient,
    'CSVExport': export,
    'Database': database,
    'DataSet': dataset,
    'DBNAME_PATTERN': database,
    'ensure_db': utils,
    'ExcelExport': export,
    'Export': export,
    'ExportFormat': export,
    'ExportXlsxWriter': export,
    'fix_view_modes': utils,
    'generate_views': utils,
    'GroupExportXlsxWriter': export,
    'GroupsTreeNode': export,
    'Home': home,
    'none_values_filtered': export,
    'OPERATOR_MAPPING': export,
    'ReportController': report,
    'Session': session,
    'SIGN_UP_REQUEST_PARAMS': home,
    'View': view,
    'WebClient': webclient,
}

def __getattr__(attr):
    module = _MOVED_TO_MAP.get(attr)
    if not module:
        raise AttributeError(f"Module {__name__!r} has not attribute {attr!r}.")

    @lazy
    def only_one_warn():
        warnings.warn(f"{__name__!r} has been split over multiple files, you'll find {attr!r} at {module.__name__!r}", DeprecationWarning, stacklevel=4)
        return getattr(module, attr)

    return only_one_warn
