# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': "Partner Autocomplete",
    'summary': "Auto-complete partner companies' data",
    'version': '1.1',
    'description': """
       Auto-complete partner companies' data
    """,
    'author': "Odoo SA",
    'category': 'Hidden/Tools',
    'depends': [
        'iap_mail',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/res_partner_views.xml',
        'views/res_company_views.xml',
        'views/res_config_settings_views.xml',
        'data/cron.xml',
    ],
    'auto_install': True,
    'assets': {
        'web.assets_backend': [
            'partner_autocomplete/static/src/scss/partner_autocomplete.scss',
            'partner_autocomplete/static/src/js/partner_autocomplete_core.js',
            'partner_autocomplete/static/src/js/partner_autocomplete_fieldchar.js',
            'partner_autocomplete/static/src/js/partner_autocomplete_many2one.js',
            'partner_autocomplete/static/src/js/web_company_autocomplete.js',
        ],
        'web.tests_assets': [
            'partner_autocomplete/static/lib/**/*',
        ],
        'web.qunit_suite_tests': [
            'partner_autocomplete/static/tests/**/*',
        ],
        'web.assets_qweb': [
            'partner_autocomplete/static/src/xml/**/*',
        ],
    },
    'license': 'LGPL-3',
}
