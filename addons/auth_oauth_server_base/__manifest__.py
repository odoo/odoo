{
    'name': 'OAuth 2.1 Authorization Server base',
    'category': 'Technical',
    'summary': 'Shared HTTP surface for OAuth 2.1 authorization servers',
    'author': 'Odoo S.A.',
    'depends': ['web'],
    'data': [
        'security/ir.access.csv',
        'views/oauth_layout_templates.xml',
        'views/oauth_client_views.xml',
        'views/oauth_client_registration_views.xml',
        'views/oauth_client_secret_show_views.xml',
    ],
    'license': 'LGPL-3',
}
