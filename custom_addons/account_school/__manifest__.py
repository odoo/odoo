# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'account_school',
    'version': '1.1',
    'summary': 'account_school',
    'sequence': 10,
    'description': """ODOO ORM common method practice""",
    'category': 'uncategoried',
    'website': 'https://www.xyz.com',
    'depends': ['base', 'contacts',],
    'data': [
        'security/ir.model.access.csv',
        'views/account_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
