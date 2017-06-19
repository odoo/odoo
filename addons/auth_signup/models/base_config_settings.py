# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools.safe_eval import safe_eval

class BaseConfigSettings(models.TransientModel):
    _inherit = 'base.config.settings'

    auth_signup_reset_password = fields.Boolean(string='Enable password reset from Login page')
    auth_signup_uninvited = fields.Boolean(string='Allow external users to sign up')
    auth_signup_template_user_id = fields.Many2one('res.users', string='Template user for new users created through signup')

    @api.model
    def get_values(self):
        res = super(BaseConfigSettings, self).get_values()
        get_param = self.env['ir.config_parameter'].sudo().get_param
        # we use safe_eval on the result, since the value of the parameter is a nonempty string
        res.update(
            auth_signup_reset_password=safe_eval(get_param('auth_signup.reset_password', 'False')),
            auth_signup_uninvited=safe_eval(get_param('auth_signup.allow_uninvited', 'False')),
            auth_signup_template_user_id=safe_eval(get_param('auth_signup.template_user_id', 'False')),
        )
        return res

    @api.multi
    def set_values(self):
        super(BaseConfigSettings, self).set_values()
        set_param = self.env['ir.config_parameter'].sudo().set_param
        # we store the repr of the values, since the value of the parameter is a required string
        set_param('auth_signup.reset_password', repr(self.auth_signup_reset_password))
        set_param('auth_signup.allow_uninvited', repr(self.auth_signup_uninvited))
        set_param('auth_signup.template_user_id', repr(self.auth_signup_template_user_id.id))

    @api.multi
    def open_template_user(self):
        action = self.env.ref('base.action_res_users').read()[0]
        action['res_id'] = self.env.ref('auth_signup.default_template_user').id
        action['views'] = [[self.env.ref('base.view_users_form').id, 'form']]
        return action
