# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Sign itsme',
    'version': '1.0',
    'category': 'Sales/Sign',
    'summary': "Sign documents with itsme® identification",
    'description': "Add support for itsme® identification when signing documents (Belgium and Netherlands only)",
    'depends': ['sign', 'iap'],
    'data': [
        'data/sign_itsme_data.xml',
        'report/sign_itsme_log_reports.xml',
        'views/sign_request_templates.xml'
    ],
    'assets': {
        'sign.assets_public_sign': [
            'sign_itsme/static/src/**/*',
        ],
        'web.assets_backend': [
            'sign_itsme/static/src/**/*',
        ],
        'web.assets_frontend': [
            'sign_itsme/static/src/**/*',
        ],
        'web.qunit_suite_tests': [
            'sign_itsme/static/tests/**/*',
        ],
    },
    'installable': True,
    'license': 'OEEL-1',
}
