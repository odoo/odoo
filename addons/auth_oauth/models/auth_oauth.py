# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class AuthOauthProvider(models.Model):
    """Class defining the configuration values of an OAuth2 provider"""

    _name = 'auth.oauth.provider'
    _description = 'OAuth2 provider'
    _order = 'sequence, name'

    name = fields.Char(string='Provider name', required=True)  # Name of the OAuth2 entity, Google, etc
    client_id = fields.Char(string='Client ID')  # Our identifier
    link_existing_users = fields.Boolean(
        string='Link Existing Users',
        help=(
            "Allow this provider to link a first OAuth login to an existing internal user "
            "with the same login. Enable this only for a trusted provider that verifies "
            "the user's email address."
        ),
    )
    auth_endpoint = fields.Char(string='Authorization URL', required=True)  # OAuth provider URL to authenticate users
    scope = fields.Char(default='openid profile email')  # OAUth user data desired to access
    validation_endpoint = fields.Char(string='UserInfo URL', required=True)  # OAuth provider URL to get user information
    data_endpoint = fields.Char()
    enabled = fields.Boolean(string='Allowed')
    icon = fields.Char(string='Custom Material Symbols Icon', default='login')
    css_class = fields.Char(string='CSS class', default='oi oi-fw text-primary')
    body = fields.Char(required=True, string="Login button label", help='Link text in Login Dialog', translate=True)
    sequence = fields.Integer(default=10)
