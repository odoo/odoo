# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Mail Plugin',
    'version': '1.0',
    'category': 'Sales/CRM',
    'sequence': 5,
    'summary': 'Allows integration with mail plugins.',
    'description': "Integrate Odoo with your mailbox, get information about contacts directly inside your mailbox, log content of emails as internal notes",
    'depends': [
        'web',
        'contacts',
        'iap'
    ],
    'data': [
        'views/mail_plugin_login.xml',
        'views/res_partner_iap_views.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
