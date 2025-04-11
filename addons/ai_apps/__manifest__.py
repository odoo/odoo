# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'AI',
    'version': '0.1',
    'sequence': 420,
    'summary': 'Artificial Intelligence Feature Management',
    'depends': [
        'base',
        'base_setup',
        'mail',
        'web',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ai_composer_data.xml',
        'views/ai_composer_views.xml',
        'views/ai_app_menu.xml',
    ],
    'demo': [
    ],
    'installable': True,
    'application': True,
    'assets': {
        'web.assets_backend': [
            'ai_apps/static/src/**/*',
        ],
    },
    'license': 'LGPL-3',
}
