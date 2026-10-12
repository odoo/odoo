# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Mass Mailing Themes',
    'summary': 'Design gorgeous mails',
    'description': """
Design gorgeous mails
    """,
    'version': '1.2',
    'sequence': 110,
    'website': 'https://www.odoo.com/app/email-marketing',
    'category': 'Marketing/Email Marketing',
    'depends': [
        'mass_mailing',
    ],
    'data': [
        'data/ir_attachment_data.xml',
        'views/mass_mailing_themes_templates.xml'
    ],
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
