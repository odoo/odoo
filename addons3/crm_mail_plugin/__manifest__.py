# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'CRM Mail Plugin',
    'version': '1.0',
    'category': 'Sales/CRM',
    'sequence': 5,
    'summary': 'Turn emails received in your mailbox into leads and log their content as internal notes.',
    'description': "Turn emails received in your mailbox into leads and log their content as internal notes.",
    'website': 'https://www.odoo.com/app/crm',
    'depends': [
        'crm',
        'mail_plugin',
    ],
    'data': [
        'views/crm_mail_plugin_lead.xml',
        'views/crm_lead_views.xml'
    ],
    'installable': True,
    'auto_install': True,
    'license': 'LGPL-3',
}
