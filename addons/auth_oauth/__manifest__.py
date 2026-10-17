# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'OAuth2 Authentication',
    'category': 'Hidden/Tools',
    'description': """
Allow users to login through OAuth2 Provider.
=============================================

Two flows are supported, selected per provider:

* Implicit: the provider hands an access token over on the callback.
* Authorization Code with Proof Key for Code Exchange (RFC 7636): the provider
  hands a single use code over, traded for an access token on the token
  endpoint, with an optional client secret for confidential clients.

The PKCE flow keeps nothing server side: the state of an authorization request
is signed and carries a nonce, and the code verifier is derived from that nonce,
from the session the request was issued to and from the provider it was issued
for. The callback derives it again instead of looking it up.
""",
    'depends': ['base', 'web', 'base_setup', 'auth_signup'],
    'data': [
        'data/auth_oauth_data.xml',
        'views/auth_oauth_views.xml',
        'views/res_config_settings_views.xml',
        'views/auth_oauth_templates.xml',
        'security/ir.access.csv',
    ],
    'assets': {
        'web.assets_frontend': [
            'auth_oauth/static/**/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
