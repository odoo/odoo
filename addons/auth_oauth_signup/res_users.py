# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2010-2012 OpenERP SA (<http://openerp.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import logging
import simplejson

import openerp
from openerp.osv import osv, fields

_logger = logging.getLogger(__name__)

class res_users(osv.Model):
    _inherit = 'res.users'

    def _auth_oauth_signin(self, cr, uid, provider, validation, params, context=None):
        # overridden to use signup method if regular oauth signin fails
        try:
            login = super(res_users, self)._auth_oauth_signin(cr, uid, provider, validation, params, context=context)

        except openerp.exceptions.AccessDenied:
            if context and context.get('no_user_creation'):
                return None
            state = simplejson.loads(params['state'])
            token = state.get('t')
            oauth_uid = validation['user_id']
            email = validation.get('email', 'provider_%s_user_%s' % (provider, oauth_uid))
            name = validation.get('name', email)
            values = {
                'name': name,
                'login': email,
                'email': email,
                'oauth_provider_id': provider,
                'oauth_uid': oauth_uid,
                'oauth_access_token': params['access_token'],
                'active': True,
            }
            _, login, _ = self.signup(cr, uid, values, token, context=context)

        return login
