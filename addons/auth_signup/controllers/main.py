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

import openerp
from openerp.modules.registry import RegistryManager

from ..res_users import SignupError

_logger = logging.getLogger(__name__)

class Controller(openerp.addons.web.http.Controller):
    _cp_path = '/auth_signup'

    @openerp.addons.web.http.jsonrequest
    def retrieve(self, req, dbname, token):
        """ retrieve the user info (name, login or email) corresponding to a signup token """
        registry = RegistryManager.get(dbname)
        with registry.cursor() as cr:
            res_partner = registry.get('res.partner')
            user_info = res_partner.signup_retrieve_info(cr, openerp.SUPERUSER_ID, token)
        return user_info

    @openerp.addons.web.http.jsonrequest
    def signup(self, req, dbname, token, name, login, password):
        """ sign up a user (new or existing)"""
        registry = RegistryManager.get(dbname)
        with registry.cursor() as cr:
            res_users = registry.get('res.users')
            values = {'name': name, 'login': login, 'password': password}
            try:
                res_users.signup(cr, openerp.SUPERUSER_ID, values, token)
            except SignupError, e:
                return {'error': openerp.tools.exception_to_unicode(e)}
            cr.commit()
        return {}

# vim:expandtab:tabstop=4:softtabstop=4:shiftwidth=4:
