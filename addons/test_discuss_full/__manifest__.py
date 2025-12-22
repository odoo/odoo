# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Test Discuss (full)',
    'version': '1.0',
    'category': 'Hidden',
    'sequence': 9877,
    'summary': 'Test of Discuss with all possible overrides installed.',
    'description': """Test of Discuss with all possible overrides installed, including feature and performance tests.""",
    'depends': [
        'calendar',
        'crm',
        'crm_livechat',
        'hr_attendance',
        'hr_fleet',
        'hr_holidays',
        'hr_homeworking',
        'im_livechat',
        'mail',
        'mail_bot',
        'project_todo',
        'website_livechat',
        'website_slides',
    ],
    "assets": {
        "web.assets_tests": [
            "test_discuss_full/static/tests/tours/*",
        ],
    },
    'installable': True,
    'license': 'LGPL-3',
}
