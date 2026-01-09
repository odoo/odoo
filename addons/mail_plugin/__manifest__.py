# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Mail Plugin',
    'category': 'Sales/CRM',
    'sequence': 5,
    'summary': 'Allows integration with mail plugins.',
    'description': "Integrate Odoo with your mailbox, get information about contacts directly inside your mailbox, log content of emails as internal notes",
    'depends': [
        'digest',
        'web',
        'contacts',
    ],
    'data': [
        'data/digest_tips.xml',
        'views/mail_plugin_login.xml',
    ],
    'auto_install': True,
    'iap_paid_service': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
