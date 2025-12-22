# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    auth_signup_reset_password = fields.Boolean(
        string='Enable password reset from Login page',
        config_parameter='auth_signup.reset_password')
    auth_signup_uninvited = fields.Selection(
        selection=[
            ('b2b', 'On invitation'),
            ('b2c', 'Free sign up'),
        ],
        string='Customer Account',
        default='b2c',
        config_parameter='auth_signup.invitation_scope')
    auth_signup_template_user_id = fields.Many2one(
        'res.users',
        string='Template user for new users created through signup',
        config_parameter='base.template_portal_user_id')
