# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

from openerp.osv import osv
from openerp import SUPERUSER_ID
from openerp.tools.translate import _

import urllib
import urllib2
import simplejson


class google_service(osv.osv_memory):
    _name = 'google.service'

    def generate_refresh_token(self, cr, uid, service, authorization_code, context=None):
        ir_config = self.pool['ir.config_parameter']
        client_id = ir_config.get_param(cr, SUPERUSER_ID, 'google_%s_client_id' % service)
        client_secret = ir_config.get_param(cr, SUPERUSER_ID, 'google_%s_client_secret' % service)
        redirect_uri = ir_config.get_param(cr, SUPERUSER_ID, 'google_redirect_uri')

        #Get the Refresh Token From Google And store it in ir.config_parameter
        headers = {"Content-type": "application/x-www-form-urlencoded"}
        data = dict(code=authorization_code, client_id=client_id, client_secret=client_secret, redirect_uri=redirect_uri, grant_type="authorization_code")
        data = urllib.urlencode(data)
        try:
            req = urllib2.Request("https://accounts.google.com/o/oauth2/token", data, headers)
            content = urllib2.urlopen(req).read()
        except urllib2.HTTPError:
            raise self.pool.get('res.config.settings').get_config_warning(cr, _("Something went wrong during your token generation. Maybe your Authorization Code is invalid or already expired"), context=context)

        content = simplejson.loads(content)
        return content.get('refresh_token')

    def _get_google_token_uri(self, cr, uid, service, scope, context=None):
        ir_config = self.pool['ir.config_parameter']
        params = {
            'scope': scope,
            'redirect_uri': ir_config.get_param(cr, SUPERUSER_ID, 'google_redirect_uri'),
            'client_id': ir_config.get_param(cr, SUPERUSER_ID, 'google_%s_client_id' % service),
            'response_type': 'code',
            'client_id': ir_config.get_param(cr, SUPERUSER_ID, 'google_%s_client_id' % service),
        }
        uri = 'https://accounts.google.com/o/oauth2/auth?%s' % urllib.urlencode(params)
        return uri

# vim:expandtab:smartindent:toabstop=4:softtabstop=4:shiftwidth=4:
