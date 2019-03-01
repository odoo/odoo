# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'CRM SMS',
    'category': 'Tools',
    'summary': 'SMS integration',
    'description': """
    Integration of SMS into CRM module
""",
    'depends': ['crm', 'sms'],
    'data': [
        'views/crm_lead_views.xml'
    ],
    'installable': True,
    'auto_install': True,
}
