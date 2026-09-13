{
    'name': 'OAuth 2.1 Authorization Server',
    'category': 'Technical',
    'summary': 'Turns this Odoo database into a generic OAuth 2.1 Authorization Server',
    'author': 'Odoo S.A.',
    'depends': ['base', 'web', 'auth_oauth_server_base'],
    'data': [
        'security/ir.access.csv',
        'views/oauth_consent_templates.xml',
        'views/oauth_resource_views.xml',
        'views/oauth_token_views.xml',
        'views/res_users_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'auth_oauth_server/static/src/scss/res_users.scss',
        ],
    },
    'license': 'LGPL-3',
}
