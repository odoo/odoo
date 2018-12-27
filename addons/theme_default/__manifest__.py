# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Default Theme',
    'description': 'Default website theme',
    'category': 'Theme/Corporate',
    'sequence': 1000,
    'version': '1.0',
    'depends': ['website', 'website_theme_install'],
    'data': [
        'data/theme_default_data.xml',
    ],
    'images': [
        'static/description/cover.png',
        'static/description/theme_default_screenshot.jpg',
    ],
    'application': False,
}
