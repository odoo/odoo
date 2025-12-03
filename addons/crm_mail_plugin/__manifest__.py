# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'CRM Mail Plugin',
    'category': 'Sales/CRM',
    'sequence': 5,
    'summary': 'Turn emails received in your mailbox into leads and log their content as internal notes.',
    'description': "Turn emails received in your mailbox into leads and log their content as internal notes.",
    'website': 'https://www.odoo.com/app/crm',
    'depends': [
        'crm',
        'mail_plugin',
    ],
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
