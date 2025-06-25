# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Default Theme',
    'description': 'Default website theme',
    'category': 'Theme',
    'sequence': 1000,
    'version': '1.0',
    'depends': ['website'],
    'data': [
        'data/generate_primary_template.xml',
    ],
    'images': [
        'static/description/cover.png',
        'static/description/theme_default_screenshot.jpg',
    ],
    'license': 'LGPL-3',
}
