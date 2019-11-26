# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'CRM Livechat',
    'category': 'Sales/CRM',
    'summary': 'Create lead from livechat conversation',
    'data': [
        'data/utm_data.xml',
    ],
    'depends': [
        'crm',
        'im_livechat'
    ],
    'data': [
        'views/templates.xml',
        'data/mail_data.xml'
    ],
    'description': 'Create new lead with using /lead command in the channel',
}
