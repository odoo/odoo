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
import datetime
import uuid

class auth_oauth2_token(osv.TransientModel):
    """Oauth2 Token Class"""

    _name = 'auth.oauth2.token'
    _description = 'OAuth2 Token'

    _columns = {
        'token': fields.char('Token', size=32, readonly=True),
        'user_id': fields.many2one('res.users', 'User', required=True, select=True, readonly=True),
        'client': fields.char('Client', help="Client Application for which the token has been generated", readonly=True, select=True), # TODO: auth.oauth2.client object
        'scope': fields.char('Scope', help="Scope for which the token has ben delivered", readonly=True, select=True),
        'expires_at': fields.datetime('Token expiration date'),
    }

    TOKEN_EXPIRATION_TIMESPAN = 3600 # in seconds

    _defaults = {
        'expires_at': lambda self, *a: datetime.datetime.utcnow() + datetime.timedelta(seconds=self.TOKEN_EXPIRATION_TIMESPAN),
    }

    def get_token(self, cr, uid, client_id="", scope="", context=None):
        token = str(uuid.uuid4()).replace('-', '')
        self.create(cr, uid, {
            'token': token,
            'user_id': uid,
            'client': client_id,
            'scope': scope,
        }, context=context)
        return {
            'access_token': token,
            'expires_in': self.TOKEN_EXPIRATION_TIMESPAN,
        }

    def tokeninfo(self, cr, uid, access_token, context=None):
        token = self.search(cr, uid, [('token', '=', access_token)], context=context)
        if not len(token):
            return { "error": "invalid_token" }
        token = self.browse(cr, uid, token[0], context=context)
        expires_at = datetime.datetime.strptime(token.expires_at[:19], '%Y-%m-%d %H:%M:%S')

        # python 2.7's datetime.timedelta supports total_seconds()
        # expires_in = int(round((expires_at - datetime.datetime.utcnow()).total_seconds()))
        delta = expires_at - datetime.datetime.utcnow()
        expires_in = (delta.microseconds + (delta.seconds + delta.days * 24 * 3600) * 10**6) / 10**6

        if expires_in <= 0:
            return { "error": "invalid_token" }

        r  = {
            "user_id": token.user_id.id,
            "scope": token.scope,
            "expires_in": expires_in,
            "audience": token.client,
        }
        return self._tokeninfo(r, token)
    def _tokeninfo(self, r, token):
        # Allows easy overloading
        if token.user_id.email: # TODO: should deliver only according to scopes
            r['email'] = token.user_id.email
        return r

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
