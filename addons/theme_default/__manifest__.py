# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Default Theme',
    'description': 'Default website theme to showcase customization possibilities.',
    'category': 'Theme/Hidden',
    'sequence': 1000,
    'version': '1.0',
    'depends': ['website'],
    'data': [
        'data/theme_default_data.xml',
        'views/theme_default_templates.xml',
    ],
    'images': [
        'static/description/cover.png',
    ],
    'application': False,
}
