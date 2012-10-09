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

from openerp import SUPERUSER_ID
from openerp.modules.registry import RegistryManager
from openerp.addons.web.controllers.main import login_and_redirect
import openerp.addons.web.common.http as openerpweb

import werkzeug

import logging
_logger = logging.getLogger(__name__)

class Controller(openerpweb.Controller):
    _cp_path = '/auth_signup'

    @openerpweb.jsonrequest
    def retrieve(self, req, dbname, token):
        """ retrieve the user info (name, login or email) corresponding to a signup token """
        registry = RegistryManager.get(dbname)
        user_info = None
        with registry.cursor() as cr:
            res_partner = registry.get('res.partner')
            user_info = res_partner.signup_retrieve_info(cr, SUPERUSER_ID, token)
        return user_info

    @openerpweb.httprequest
    def signup(self, req, dbname, token, name, login, password):
        """ sign up a user (new or existing), and log it in """
        url = '/'
        registry = RegistryManager.get(dbname)
        with registry.cursor() as cr:
            try:
                res_users = registry.get('res.users')
                values = {'name': name, 'login': login, 'password': password}
                credentials = res_users.signup(cr, SUPERUSER_ID, values, token)
                cr.commit()
                return login_and_redirect(req, *credentials)
            except Exception as e:
                # signup error
                _logger.exception('error when signup')
                url = "/#action=login&error_message=%s" % werkzeug.urls.url_quote(e.message)
        return werkzeug.utils.redirect(url)

# vim:expandtab:tabstop=4:softtabstop=4:shiftwidth=4:
