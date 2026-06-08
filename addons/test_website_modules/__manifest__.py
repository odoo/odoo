# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Website Modules Test',
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
        'website_livechat',
        'website_crm_iap_reveal',
        'website_sale',
    ],
    'assets': {
        'web.assets_tests': [
            'test_website_modules/static/tests/**/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
