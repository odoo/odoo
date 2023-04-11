# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Website Modules Test',
    'version': '1.0',
    'category': 'Hidden',
    'sequence': 9876,
    'description': """This module contains tests related to website modules.
It allows to test website business code when another website module is
installed.""",
    'depends': [
        'theme_default',
        'website',
        'website_blog',
        'website_event_sale',
        'website_slides',
    ],
    'installable': True,
    'assets': {
        'web.assets_tests': [
            'test_website_modules/static/tests/**/*',
        ],
    },
    'license': 'LGPL-3',
}
