# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2012-today OpenERP SA (<http://www.openerp.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################
import logging

import werkzeug

import openerp
from openerp import SUPERUSER_ID
from openerp.modules.registry import RegistryManager

_logger = logging.getLogger(__name__)

class Controller(openerp.addons.web.http.Controller):
    _cp_path = '/auth_reset_password'

    @openerp.addons.web.http.httprequest
    def reset_password(self, req, dbname, login):
        """ retrieve user, and perform reset password """
        url = '/'
        registry = RegistryManager.get(dbname)
        with registry.cursor() as cr:
            try:
                res_users = registry.get('res.users')
                res_users.reset_password(cr, SUPERUSER_ID, login)
                cr.commit()
                message = 'An email has been sent with credentials to reset your password'
            except Exception as e:
                # signup error
                _logger.exception('error when resetting password')
                message = e.message
        url = "/#action=login&error_message=%s" % werkzeug.urls.url_quote(message)
        return werkzeug.utils.redirect(url)

# vim:expandtab:tabstop=4:softtabstop=4:shiftwidth=4:
