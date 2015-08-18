# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import osv, fields
from openerp.tools.safe_eval import safe_eval

class base_config_settings(osv.TransientModel):
    _inherit = 'base.config.settings'

    _columns = {
        'auth_signup_reset_password': fields.boolean('Enable password reset from Login page',
            help="This allows users to trigger a password reset from the Login page."),
        'auth_signup_uninvited': fields.boolean('Allow external users to sign up',
            help="If unchecked, only invited users may sign up."),
        'auth_signup_template_user_id': fields.many2one('res.users',
            string='Template user for new users created through signup'),
    }

    def get_default_auth_signup_template_user_id(self, cr, uid, fields, context=None):
        icp = self.pool.get('ir.config_parameter')
        # we use safe_eval on the result, since the value of the parameter is a nonempty string
        return {
            'auth_signup_reset_password': safe_eval(icp.get_param(cr, uid, 'auth_signup.reset_password', 'False')),
            'auth_signup_uninvited': safe_eval(icp.get_param(cr, uid, 'auth_signup.allow_uninvited', 'False')),
            'auth_signup_template_user_id': safe_eval(icp.get_param(cr, uid, 'auth_signup.template_user_id', 'False')),
        }

    def set_auth_signup_template_user_id(self, cr, uid, ids, context=None):
        config = self.browse(cr, uid, ids[0], context=context)
        icp = self.pool.get('ir.config_parameter')
        # we store the repr of the values, since the value of the parameter is a required string
        icp.set_param(cr, uid, 'auth_signup.reset_password', repr(config.auth_signup_reset_password))
        icp.set_param(cr, uid, 'auth_signup.allow_uninvited', repr(config.auth_signup_uninvited))
        icp.set_param(cr, uid, 'auth_signup.template_user_id', repr(config.auth_signup_template_user_id.id))
