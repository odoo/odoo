# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Cohort View',
    'summary': 'Basic Cohort view for odoo',
    'category': 'Hidden',
    'depends': ['web'],
    'assets': {
        'web.assets_backend': [
            'web_cohort/static/src/**/*',
        ],
        'web.qunit_suite_tests': [
            'web_cohort/static/tests/**/*.js',
        ],
    },
    'auto_install': True,
    'license': 'OEEL-1',
}
