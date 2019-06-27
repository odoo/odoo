# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'SMS Marketing',
    'summary': 'Design, send and track SMS',
    'description': '',
    'version': '1.0',
    'category': 'Marketing/Email Marketing',
    'depends': [
        'mass_mailing',
        'sms',
    ],
    'data': [
        'data/utm_data.xml',
        'data/mass_mailing_sms_data.xml',
        'security/ir.model.access.csv',
        'views/mass_mailing_menus.xml',
        'views/sms_statistics_views.xml',
        'views/mass_mailing_views.xml',
        # 'views/link_tracker_views.xml',
        'report/sms_statistics_report_views.xml',
        'wizard/sms_composer_views.xml',
        'wizard/mass_sms_test_views.xml',
    ],
    'demo': [
        # 'data/mass_mailing_sms_demo.xml',
    ],
}
