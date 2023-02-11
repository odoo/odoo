# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AuthOAuthProvider(models.Model):
    """Class defining the configuration values of an OAuth2 provider"""

    _name = 'auth.oauth.provider'
    _description = 'OAuth2 provider'
    _order = 'sequence, name'

    name = fields.Char(string='Provider name', required=True)  # Name of the OAuth2 entity, Google, etc
    client_id = fields.Char(string='Client ID')  # Our identifier
    auth_endpoint = fields.Char(string='Authorization URL', required=True)  # OAuth provider URL to authenticate users
    scope = fields.Char(default='openid profile email')  # OAUth user data desired to access
    validation_endpoint = fields.Char(string='UserInfo URL', required=True)  # OAuth provider URL to get user information
    data_endpoint = fields.Char()
    enabled = fields.Boolean(string='Allowed')
    css_class = fields.Char(string='CSS class', default='fa fa-fw fa-sign-in text-primary')
    body = fields.Char(required=True, string="Login button label", help='Link text in Login Dialog', translate=True)
    sequence = fields.Integer(default=10)
