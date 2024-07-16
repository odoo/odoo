# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'SMS Marketing',
    'summary': 'Design, send and track SMS',
    'version': '1.0',
    'category': 'Marketing/Email Marketing',
    'sequence': 245,
    'depends': [
        'portal',
        'mass_mailing',
        'sms',
    ],
    'data': [
        'data/utm_data.xml',
        'security/ir.model.access.csv',
        'report/mailing_trace_report_views.xml',
        'views/mailing_list_views.xml',
        'views/mailing_contact_views.xml',
        'views/mailing_trace_views.xml',
        'views/mailing_mailing_views.xml',
        'views/mass_mailing_sms_templates_portal.xml',
        'views/utm_campaign_views.xml',
        'views/mailing_sms_menus.xml',
        'wizard/sms_composer_views.xml',
        'wizard/mailing_sms_test_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'mass_mailing_sms/static/src/**',
        ],
    },
    'demo': [
        'data/utm_demo.xml',
        'data/mailing_list_demo.xml',
        'data/mailing_demo.xml',
    ],
    'application': True,
    'license': 'LGPL-3',
}
