# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import SUPERUSER_ID
from openerp.osv import fields, osv


class base_config_settings(osv.TransientModel):
    _inherit = "base.config.settings"

    def _get_drive_uri(self, cr, uid, ids, field_name, arg, context=None):
        return {
            wizard_id: self.default_get(cr, uid, ['google_drive_uri']).get('google_drive_uri')
            for wizard_id in ids
        }

    def _get_wizard_ids(self, cr, uid, ids, context=None):
        result = []
        if any(rec.key in ['google_drive_client_id', 'google_redirect_uri'] for rec in self.browse(cr, uid, ids, context=context)):
            result.extend(self.pool['base.config.settings'].search(cr, uid, [], context=context))
        return result

    _columns = {
        'google_drive_authorization_code': fields.char('Authorization Code'),
        'google_drive_uri': fields.function(_get_drive_uri, string='URI', help="The URL to generate the authorization code from Google", type="char", store={
            'ir.config_parameter': (_get_wizard_ids, None, 20),
        }),  # TODO: 1. in master, remove the store, there is no reason for this field to be stored. It's just a dynamic link.
             # TODO: 2. when converted to the new API, the code to get the default value can be moved to the compute method directly, and the default value can be removed
             #          the only reason the default value is defined is because function fields are not computed in draft mode in the old API.
    }
    _defaults = {
        'google_drive_uri': lambda s, cr, uid, c: s.pool['google.service']._get_google_token_uri(cr, uid, 'drive', scope=s.pool['google.drive.config'].get_google_scope(), context=c),
        'google_drive_authorization_code': lambda s, cr, uid, c: s.pool['ir.config_parameter'].get_param(cr, SUPERUSER_ID, 'google_drive_authorization_code', context=c),
    }

    def set_google_authorization_code(self, cr, uid, ids, context=None):
        ir_config_param = self.pool['ir.config_parameter']
        config = self.browse(cr, uid, ids[0], context)
        auth_code = config.google_drive_authorization_code
        if auth_code and auth_code != ir_config_param.get_param(cr, uid, 'google_drive_authorization_code', context=context):
            refresh_token = self.pool['google.service'].generate_refresh_token(cr, uid, 'drive', config.google_drive_authorization_code, context=context)
            ir_config_param.set_param(cr, uid, 'google_drive_authorization_code', auth_code, groups=['base.group_system'])
            ir_config_param.set_param(cr, uid, 'google_drive_refresh_token', refresh_token, groups=['base.group_system'])
