# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ast import literal_eval

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    auth_signup_reset_password = fields.Boolean(string='Enable password reset from Login page')
    auth_signup_uninvited = fields.Selection([
        ('b2b', 'On invitation (B2B)'),
        ('b2c', 'Free sign up (B2C)'),
    ], string='Customer Account')
    auth_signup_template_user_id = fields.Many2one('res.users', string='Template user for new users created through signup')

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        get_param = self.env['ir.config_parameter'].sudo().get_param
        # the value of the parameter is a nonempty string
        res.update(
            auth_signup_reset_password=get_param('auth_signup.reset_password', 'False').lower() == 'true',
            auth_signup_uninvited='b2c' if get_param('auth_signup.allow_uninvited', 'False').lower() == 'true' else 'b2b',
            auth_signup_template_user_id=literal_eval(get_param('auth_signup.template_user_id', 'False')),
        )
        return res

    @api.multi
    def set_values(self):
        super(ResConfigSettings, self).set_values()
        set_param = self.env['ir.config_parameter'].sudo().set_param
        # we store the repr of the values, since the value of the parameter is a required string
        set_param('auth_signup.reset_password', repr(self.auth_signup_reset_password))
        set_param('auth_signup.allow_uninvited', repr(self.auth_signup_uninvited == 'b2c'))
        set_param('auth_signup.template_user_id', repr(self.auth_signup_template_user_id.id))

    @api.multi
    def open_template_user(self):
        action = self.env.ref('base.action_res_users').read()[0]
        action['res_id'] = literal_eval(self.env['ir.config_parameter'].sudo().get_param('auth_signup.template_user_id', 'False'))
        action['views'] = [[self.env.ref('base.view_users_form').id, 'form']]
        return action
