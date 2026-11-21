# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Events Digital Wallet',
    'version': '1.0',
    'category': 'Marketing/Events',
    'summary': 'Sign event passes with certificates managed by Odoo',
    'depends': ['website_event', 'certificate'],
    'data': [
        'views/certificate_certificate_views.xml',
        'views/event_event_views.xml',
        'views/res_config_settings_views.xml',
        'views/event_registration_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'website_event_wallet/static/src/interactions/registration_wallet.js',
            'website_event_wallet/static/src/interactions/apple.js',
        ],
    },
    'external_dependencies': {'python': ['asn1crypto', 'cryptography', 'PIL']},
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
