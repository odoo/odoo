# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Project Mail Plugin',
    'category': 'Services/Project',
    'sequence': 5,
    'summary': 'Integrate your inbox with projects',
    'description': "Turn emails received in your mailbox into tasks and log their content as internal notes.",
    'website': 'https://www.odoo.com/app/project',
    'depends': [
        'project',
        'mail_plugin',
    ],
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
