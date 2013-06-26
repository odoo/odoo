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

import urllib
import urllib2
import simplejson


class base_config_settings(osv.osv):
    _inherit = "base.config.settings"

    def onchange_google_authorization_code(self, cr, uid, ids, service, authorization_code, context=None):
        if authorization_code:
            ir_config = self.pool['ir.config_parameter']
            client_id = ir_config.get_param(cr, SUPERUSER_ID, 'google_%s_client_id' % service)
            client_secret = ir_config.get_param(cr, SUPERUSER_ID, 'google_%s_client_secret' % service)
            redirect_uri = ir_config.get_param(cr, SUPERUSER_ID, 'google_redirect_uri')

            #Get the Refresh Token From Google And store it in ir.config_parameter
            data = {
                'code': authorization_code,
                'client_id': client_id,
                'client_secret': client_secret,
                'redirect_uri': redirect_uri,
                'grant_type': "authorization_code",
            }
            resp, content = urllib2.urlopen("https://accounts.google.com/o/oauth2/token", urllib.urlencode(data))
            content = simplejson.loads(content)
            if 'refresh_token' in content.keys():
                ir_config.set_param(cr, uid, 'google_%s_refresh_token' % service, content['refresh_token'])
        return {}

    def _get_google_token_uri(self, cr, uid, service, context=None):
        ir_config = self.pool['ir.config_parameter']
        params = {
            'scope': 'https://www.googleapis.com/auth/drive',
            'redirect_uri': ir_config.get_param(cr, SUPERUSER_ID, 'google_redirect_uri'),
            'client_id': ir_config.get_param(cr, SUPERUSER_ID, 'google_%s_client_id' % service),
            'response_type': 'code',
            'client_id': ir_config.get_param(cr, SUPERUSER_ID, 'google_%s_client_id' % service),
        }
        uri = 'https://accounts.google.com/o/oauth2/auth?%s' % urllib.urlencode(params)
        return uri

# vim:expandtab:smartindent:toabstop=4:softtabstop=4:shiftwidth=4:
