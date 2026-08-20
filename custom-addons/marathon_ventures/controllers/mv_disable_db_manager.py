# -*- coding: utf-8 -*-
"""Block the public database-manager surface.

Hiding the "Manage Databases" link in CSS is cosmetic - anyone who
edits the DOM in devtools OR types a /web/database/* URL directly
can still reach the page. To actually close the surface we override
every route on `odoo.addons.web.controllers.database.Database` and
return HTTP 404 for anonymous callers.

Applies to:
    /web/database/selector
    /web/database/manager
    /web/database/create
    /web/database/duplicate
    /web/database/drop
    /web/database/backup
    /web/database/restore
    /web/database/change_password
    /web/database/list           (JSON-RPC; returns [] so anonymous
                                  callers can't enumerate DB names)

To re-enable database management for a genuine admin task, uninstall
the marathon_ventures module or use odoo-bin's CLI on the server.
"""
import logging

import werkzeug.exceptions

from odoo import http
from odoo.addons.web.controllers.database import Database

_logger = logging.getLogger(__name__)


class MvDatabaseHardened(Database):
    """Override the anonymous database-manager surface.

    Every method here raises HTTP 404 unconditionally. Odoo's
    controller dispatch picks up the subclass in addon-loading
    order, so as long as marathon_ventures is installed our
    behaviour replaces the stock one.
    """

    def _mv_deny(self, endpoint):
        _logger.warning(
            "mv_disable_db_manager: blocked anonymous access to %s",
            endpoint,
        )
        raise werkzeug.exceptions.NotFound()

    # ----------------------------------------------------------------
    # HTTP routes
    # ----------------------------------------------------------------
    @http.route('/web/database/selector', type='http', auth='none')
    def selector(self, **kw):
        return self._mv_deny('selector')

    @http.route('/web/database/manager', type='http', auth='none')
    def manager(self, **kw):
        return self._mv_deny('manager')

    @http.route('/web/database/create', type='http', auth='none',
                methods=['POST'], csrf=False)
    def create(self, master_pwd, name, lang, password, phone=None,
               login='admin', country_code=None, **kw):
        return self._mv_deny('create')

    @http.route('/web/database/duplicate', type='http', auth='none',
                methods=['POST'], csrf=False)
    def duplicate(self, master_pwd, name, new_name, neutralize_database=False):
        return self._mv_deny('duplicate')

    @http.route('/web/database/drop', type='http', auth='none',
                methods=['POST'], csrf=False)
    def drop(self, master_pwd, name):
        return self._mv_deny('drop')

    @http.route('/web/database/backup', type='http', auth='none',
                methods=['POST'], csrf=False)
    def backup(self, master_pwd, name, backup_format='zip'):
        return self._mv_deny('backup')

    @http.route('/web/database/restore', type='http', auth='none',
                methods=['POST'], csrf=False)
    def restore(self, master_pwd, backup_file, name, copy=False):
        return self._mv_deny('restore')

    @http.route('/web/database/change_password', type='http', auth='none',
                methods=['POST'], csrf=False)
    def change_password(self, master_pwd, master_pwd_new):
        return self._mv_deny('change_password')

    # ----------------------------------------------------------------
    # JSON-RPC route: also refuse to enumerate database names.
    # ----------------------------------------------------------------
    @http.route('/web/database/list', type='jsonrpc', auth='none')
    def list(self):
        return []
