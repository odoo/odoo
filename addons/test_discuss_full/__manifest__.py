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
        'hr_holidays',
        'im_livechat',
        'mail',
        'mail_bot',
        'note',
        'website_livechat',
    ],
    'installable': True,
    'license': 'LGPL-3',
}
