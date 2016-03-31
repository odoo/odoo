# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Trinh General Customize',
    'version': '1.0',
    'category': 'Sales Management',
    'sequence': 15,
    'summary': 'Trinh general customize',
    'description': """
    To:
    -- invisible invoicing_policy, to_weight
        fields in product form
    """,
    'website': 'https://www.odoo.com',
    'depends': ['sale'],
    'data': [
        'views/sale_view.xml',
    ],
    'demo': [],
    'css': [],
    'installable': True,
    'auto_install': False,
    'application': True,
}
