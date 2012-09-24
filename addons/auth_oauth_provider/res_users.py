#!/usr/bin/env python
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2010-2012 OpenERP s.a. (<http://openerp.com>).
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
from openerp.osv import osv, fields
import random
import string

class res_users(osv.osv):
    _inherit = 'res.users'

    _columns = {
        # TODO: partial implementation supporting only one client_id for the moment.
        'last_oauth_token': fields.char('Last OAuth Token', readonly=True, invisible=True),
        'last_oauth_token_scope': fields.char('Last OAuth Token Scope', readonly=True, invisible=True),
    }

    def auth_oauth_provider_get_token(self, cr, uid, client_id="", scope="", context=None):
        chars = string.ascii_uppercase + string.ascii_lowercase + string.digits
        token = ''.join(random.choice(chars) for x in range(random.randrange(16, 24)))
        self.write(cr, uid, [uid], {
            "last_oauth_token": token,
            "last_oauth_token_scope": scope,
        }, context=context)
        return token

    def auth_oauth_provider_tokeninfo(self, cr, uid, access_token, context=None):
        user_id = self.search(cr, uid, [('last_oauth_token', '=', access_token)], context=context)
        if len(user_id) != 1:
            return {
                "error": "invalid_token"
            }
        user = self.browse(cr, uid, user_id[0], context=context)
        if access_token == user.last_oauth_token:
            return {
                "user_id": uid,
                "scope": user.last_oauth_token_scope,
                "email": user.partner_id.email or '', # TODO: should deliver only according to scopes
                "scope": user.last_oauth_token_scope,
                #"audience": "8819981768.apps.googleusercontent.com",
                #"expires_in": 436
            }
        else:
            return {
                "error": "invalid_token"
            }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
