# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Marketing Automation Tests",
    'version': "1.1",
    'summary': "Test Suite for Automated Marketing Campaigns",
    'category': "Hidden",
    'depends': [
        'marketing_automation',
        'marketing_automation_sms',
        'test_mail',
        'test_mail_enterprise',
        'test_mail_full',
        'test_mail_sms',
        'test_mass_mailing',
    ],
    'data': [
        'security/ir.model.access.csv',
    ],
    'license': 'OEEL-1',
}
