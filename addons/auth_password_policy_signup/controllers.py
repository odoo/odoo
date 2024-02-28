# -*- coding: utf-8 -*-

from odoo.http import request
from odoo.addons.auth_signup.controllers.main import AuthSignupHome

class AddPolicyData(AuthSignupHome):
    def get_auth_signup_config(self):
        d = super(AddPolicyData, self).get_auth_signup_config()
        d['password_minimum_length'] = request.env['ir.config_parameter'].sudo().get_param('auth_password_policy.minlength')
        return d
