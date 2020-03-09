# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'CRM Livechat',
    'category': 'Sales/CRM',
    'summary': 'Create lead from livechat conversation',
    'data': [
        'security/crm_livechat_security.xml',
        'data/utm_data.xml',
        'data/mail_data.xml',
        'views/res_config_settings_views.xml',
        'views/templates.xml',
    ],
    'depends': [
        'crm',
        'im_livechat'
    ],
    'description': 'Create new lead with using /lead command in the channel',
    'auto_install': True
}
