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
        'auth_oauth_google_enabled' : fields.boolean('Allow users to login with Google'),
        'auth_oauth_google_client_id' : fields.char('Client ID'),
        'auth_oauth_facebook_enabled' : fields.boolean('Allow users to login with Facebook'),
        'auth_oauth_facebook_client_id' : fields.char('Client ID'),
    }

    def get_default_allow(self, cr, uid, fields, context=None):
        google_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'auth_oauth', 'provider_google')[1]
        rg = self.pool.get('auth.oauth.provider').read(cr, uid, [google_id], ['enabled'], context=context)
        facebook_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'auth_oauth', 'provider_facebook')[1]
        rf = self.pool.get('auth.oauth.provider').read(cr, uid, [facebook_id], ['enabled'], context=context)
        return {
            'auth_oauth_google_enabled': rg[0]['enabled'],
            'auth_oauth_facebook_enabled': rf[0]['enabled']
        }

    def set_allow(self, cr, uid, ids, context=None):
        google_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'auth_oauth', 'provider_google')[1]
        facebook_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'auth_oauth', 'provider_facebook')[1]
        config = self.browse(cr, uid, ids[0], context=context)
        self.pool.get('auth.oauth.provider').write(cr, uid, [google_id], {'enabled':config.auth_oauth_google_enabled})
        self.pool.get('auth.oauth.provider').write(cr, uid, [facebook_id], {'enabled':config.auth_oauth_facebook_enabled})

    # def get_default_client_ids(self, cr, uid, fields, context=None):
    #     google_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'auth_oauth', 'provider_google')[1]
    #     facebook_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'auth_oauth', 'provider_facebook')[1]
    #     return {
    #         'auth_oauth_google_client_id': icp.get_param(cr, uid, 'auth.auth_oauth_google_client_id', "Set by the user") or False
    #     }

    # def set_client_ids(self, cr, uid, ids, context=None):
    #     provider_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'auth_oauth', 'provider_goole')


    #     config = self.browse(cr, uid, ids[0], context=context)
    #     icp = self.pool.get('ir.config_parameter')
    #     icp.set_param(cr, uid, 'auth.google_client_id', config.google_client_id)

    # def get_default_facebook_client_id(self, cr, uid, fields, context=None):
    #     icp = self.pool.get('ir.config_parameter')
    #     return {
    #         'facebook_client_id': icp.get_param(cr, uid, 'auth.facebook_client_id', "Set by the user") or False
    #     }

    # def set_facebook_client_id(self, cr, uid, ids, context=None):
    #     config = self.browse(cr, uid, ids[0], context=context)
    #     icp = self.pool.get('ir.config_parameter')
    #     icp.set_param(cr, uid, 'auth.facebook_client_id', config.facebook_client_id)