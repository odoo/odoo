# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Mass Mailing Themes',
    'summary': 'Design gorgeous mails',
    'description': """
Design gorgeous mails
    """,
    'version': '1.1',
    'sequence': 110,
    'website': 'https://www.odoo.com/app/mailing',
    'category': 'Marketing/Email Marketing',
    'depends': [
        'mass_mailing',
    ],
    'data': [
        'views/mass_mailing_themes_templates.xml'
    ],
    'installable': True,
    'auto_install': True,
    'license': 'LGPL-3',
}
