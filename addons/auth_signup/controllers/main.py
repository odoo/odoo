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
from openerp import http
from openerp.http import request
from openerp.modules.registry import RegistryManager
from ..res_users import SignupError

_logger = logging.getLogger(__name__)

class Controller(http.Controller):

    @http.route('/auth_signup/get_config', type='json', auth="none")
    def get_config(self, dbname):
        """ retrieve the module config (which features are enabled) for the login page """
        registry = RegistryManager.get(dbname)
        with registry.cursor() as cr:
            icp = registry.get('ir.config_parameter')
            config = {
                'signup': icp.get_param(cr, openerp.SUPERUSER_ID, 'auth_signup.allow_uninvited') == 'True',
                'reset_password': icp.get_param(cr, openerp.SUPERUSER_ID, 'auth_signup.reset_password') == 'True',
            }
        return config

    @http.route('/auth_signup/retrieve', type='json', auth="none")
    def retrieve(self, dbname, token):
        """ retrieve the user info (name, login or email) corresponding to a signup token """
        registry = RegistryManager.get(dbname)
        with registry.cursor() as cr:
            res_partner = registry.get('res.partner')
            user_info = res_partner.signup_retrieve_info(cr, openerp.SUPERUSER_ID, token)
        return user_info

    @http.route('/auth_signup/signup', type='json', auth="none")
    def signup(self, dbname, token, **values):
        """ sign up a user (new or existing)"""
        try:
            self._signup_with_values(dbname, token, values)
        except SignupError, e:
            return {'error': openerp.tools.exception_to_unicode(e)}
        return {}

    def _signup_with_values(self, dbname, token, values):
        registry = RegistryManager.get(dbname)
        with registry.cursor() as cr:
            res_users = registry.get('res.users')
            res_users.signup(cr, openerp.SUPERUSER_ID, values, token)

    @http.route('/auth_signup/reset_password', type='json', auth="none")
    def reset_password(self, dbname, login):
        """ retrieve user, and perform reset password """
        registry = RegistryManager.get(dbname)
        with registry.cursor() as cr:
            try:
                res_users = registry.get('res.users')
                res_users.reset_password(cr, openerp.SUPERUSER_ID, login)
                cr.commit()
            except Exception as e:
                # signup error
                _logger.exception('error when resetting password')
                raise(e)
        return True

# vim:expandtab:tabstop=4:softtabstop=4:shiftwidth=4:
