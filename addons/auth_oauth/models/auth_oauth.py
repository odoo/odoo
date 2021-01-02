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
    auth_endpoint = fields.Char(string='Authentication URL', required=True)  # OAuth provider URL to authenticate users
    scope = fields.Char()  # OAUth user data desired to access
    validation_endpoint = fields.Char(string='Validation URL', required=True)  # OAuth provider URL to validate tokens
    data_endpoint = fields.Char(string='Data URL')
    access_token_location = fields.Selection([
            ('bearer', 'Bearer Authorization header'),
            ('oauth', 'OAuth Authorization header'),
            ('uri', 'URI query-string parameter (deprecated)')
            ], default='bearer', string="Access token location", required=True,
            help="Where to place Access Token when accessing provider's endpoints.")
    enabled = fields.Boolean(string='Allowed')
    css_class = fields.Char(string='CSS class', default='fa fa-fw fa-sign-in text-primary')
    body = fields.Char(required=True, help='Link text in Login Dialog', translate=True)
    sequence = fields.Integer(default=10)
