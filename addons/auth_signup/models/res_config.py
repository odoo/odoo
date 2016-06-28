# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools.safe_eval import safe_eval

class BaseConfigSettings(models.TransientModel):
    _inherit = 'base.config.settings'

    auth_signup_reset_password = fields.Boolean(string='Enable password reset from Login page', help="This allows users to trigger a password reset from the Login page.")
    auth_signup_uninvited = fields.Boolean(string='Allow external users to sign up', help="If unchecked, only invited users may sign up.")
    auth_signup_template_user_id = fields.Many2one('res.users', string='Template user for new users created through signup')

    @api.model
    def get_default_auth_signup_template_user_id(self, fields):
        IrConfigParam = self.env['ir.config_parameter']
        # we use safe_eval on the result, since the value of the parameter is a nonempty string
        return {
            'auth_signup_reset_password': safe_eval(IrConfigParam.get_param('auth_signup.reset_password', 'False')),
            'auth_signup_uninvited': safe_eval(IrConfigParam.get_param('auth_signup.allow_uninvited', 'False')),
            'auth_signup_template_user_id': safe_eval(IrConfigParam.get_param('auth_signup.template_user_id', 'False')),
        }

    @api.multi
    def set_auth_signup_template_user_id(self):
        self.ensure_one()
        IrConfigParam = self.env['ir.config_parameter']
        # we store the repr of the values, since the value of the parameter is a required string
        IrConfigParam.set_param('auth_signup.reset_password', repr(self.auth_signup_reset_password))
        IrConfigParam.set_param('auth_signup.allow_uninvited', repr(self.auth_signup_uninvited))
        IrConfigParam.set_param('auth_signup.template_user_id', repr(self.auth_signup_template_user_id.id))
