# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Website Report',
    'category': 'Website',
    'summary': 'Website Editor on reports',
    'version': '1.0',
    'description': """
Use the website editor to customize your reports.
        """,
    'author': 'Odoo S.A.',
    'depends': ['base', 'website', 'report'],
    'data': [
        'views/report_templates.xml'
    ],
    'installable': True,
    'auto_install': True,
}
