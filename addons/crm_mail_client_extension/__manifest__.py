# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'CRM Mail Client Extension',
    'version': '1.0',
    'category': 'Sales/CRM',
    'sequence': 5,
    'summary': 'Turn emails received in your mailbox into leads and log their content as internal notes.',
    'description': "Turn emails received in your mailbox into leads and log their content as internal notes.",
    'website': 'https://www.odoo.com/page/crm',
    'depends': [
        'crm',
        'mail_client_extension',
    ],
    'data': [
        'views/crm_mail_client_extension_lead.xml'
    ],
    'installable': True,
    'application': False,
    'auto_install': True
}
