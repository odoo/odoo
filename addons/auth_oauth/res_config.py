# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2012-Today OpenERP SA (<http://www.openerp.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################

from openerp.osv import osv, fields

import logging
_logger = logging.getLogger(__name__)

class base_config_settings(osv.TransientModel):
    _inherit = 'base.config.settings'

    _columns = {
        'auth_oauth_google_enabled' : fields.boolean('Allow users to sign in with Google'),
        'auth_oauth_google_client_id' : fields.char('Client ID'),
        'auth_oauth_facebook_enabled' : fields.boolean('Allow users to sign in with Facebook'),
        'auth_oauth_facebook_client_id' : fields.char('Client ID'),
    }

    def default_get(self, cr, uid, fields, context=None):
        res = super(base_config_settings, self).default_get(cr, uid, fields, context=context)
        res.update(self.get_oauth_providers(cr, uid, fields, context=context))
        return res

    def get_oauth_providers(self, cr, uid, fields, context=None):
        google_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'auth_oauth', 'provider_google')[1]
        facebook_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'auth_oauth', 'provider_facebook')[1]
        rg = self.pool.get('auth.oauth.provider').read(cr, uid, [google_id], ['enabled','client_id'], context=context)
        rf = self.pool.get('auth.oauth.provider').read(cr, uid, [facebook_id], ['enabled','client_id'], context=context)
        return {
            'auth_oauth_google_enabled': rg[0]['enabled'],
            'auth_oauth_google_client_id': rg[0]['client_id'],
            'auth_oauth_facebook_enabled': rf[0]['enabled'],
            'auth_oauth_facebook_client_id': rf[0]['client_id'],
        }

    def set_oauth_providers(self, cr, uid, ids, context=None):
        google_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'auth_oauth', 'provider_google')[1]
        facebook_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'auth_oauth', 'provider_facebook')[1]
        config = self.browse(cr, uid, ids[0], context=context)
        rg = {
            'enabled':config.auth_oauth_google_enabled,
            'client_id':config.auth_oauth_google_client_id,
        }
        rf = {
            'enabled':config.auth_oauth_facebook_enabled,
            'client_id':config.auth_oauth_facebook_client_id,
        }
        self.pool.get('auth.oauth.provider').write(cr, uid, [google_id], rg)
        self.pool.get('auth.oauth.provider').write(cr, uid, [facebook_id], rf)

