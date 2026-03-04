# -*- coding: utf-8 -*-
{
    'name': 'Web Custom Theme',
    'summary': 'Customizes the Odoo backend color palette',
    'version': '19.0.2.0.0',
    'category': 'Theme/Backend',
    'author': 'GRP',
    'depends': ['web', 'gov_base'],
    'data': [
        'views/web_layout_templates.xml',
    ],
    'assets': {
        'web.assets_backend': [
            (
                'before',
                'web/static/src/scss/primary_variables.scss',
                'web_custom_theme/static/src/scss/primary_variables.scss',
            ),
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}

