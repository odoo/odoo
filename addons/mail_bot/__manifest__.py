# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'OdooBot',
    'version': '1.2',
    'category': 'Productivity/Discuss',
    'summary': 'Add OdooBot in discussions',
    'description': "",
    'website': 'https://www.odoo.com/page/discuss',
    'depends': ['mail'],
    'auto_install': True,
    'installable': True,
    'application': False,
    'data': [
        'views/res_users_views.xml',
        'data/mailbot_data.xml',
    ],
    'demo': [
        'data/mailbot_demo.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'mail_bot/static/src/bugfix/bugfix.js',
            'mail_bot/static/src/models/messaging_initializer/messaging_initializer.js',
            'mail_bot/static/src/scss/odoobot_style.scss',
            'mail_bot/static/src/bugfix/bugfix.scss',
        ],
        'web.tests_assets': [
            'mail_bot/static/tests/**/*',
        ],
        'web.qunit_suite_tests': [
            'mail_bot/static/src/bugfix/bugfix_tests.js',
            'mail_bot/static/src/models/messaging_initializer/messaging_initializer_tests.js',
        ],
        'web.assets_qweb': [
            'mail_bot/static/src/bugfix/bugfix.xml',
        ],
    }
}
