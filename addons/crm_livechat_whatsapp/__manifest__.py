# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'CRM Livechat whatsapp',
    'category': 'Sales/CRM',
    'summary': 'Create lead from whatsapp conversation',
    'data': [
        'data/utm_data.xml',
    ],
    'depends': [
        'crm',
        'im_livechat',
        'whatsapp'
    ],
    'description': 'Create new lead with using /lead command in the channel',
    'auto_install': True,
    'license': 'LGPL-3',
}
