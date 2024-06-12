# -*- coding: utf-8 -*-

{
    'name': 'Mail Tests',
    'version': '1.0',
    'category': 'Hidden',
    'sequence': 9876,
    'summary': 'Mail Tests: performances and tests specific to mail',
    'description': """This module contains tests related to mail. Those are
present in a separate module as it contains models used only to perform
tests independently to functional aspects of other models. """,
    'depends': [
        'mail',
        'test_performance',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/test_mail_security.xml',
        'data/data.xml',
        'data/mail_template_data.xml',
        'data/subtype_data.xml',
    ],
    'assets': {
        'web.qunit_suite_tests': [
            'test_mail/static/tests/*',
        ],
        'web.qunit_mobile_suite_tests': [
            'test_mail/static/tests/mobile/activity_tests.js',
        ],
        'web.tests_assets': [
            'test_mail/static/tests/helpers/*',
        ],
    },
    'installable': True,
    'license': 'LGPL-3',
}
