# -*- coding: utf-8 -*-
{
    'name': "Multi Company Guidelines - Sample Module",

    'description': """
        Sample module regarding coding guidelines for multi-company environments.
    """,
    'author': "Odoo S.A.",
    'website': "https://www.odoo.com",
    'category': 'Uncategorized',
    'version': '1.0',
    'depends': ['web', 'contacts'],  # contacts to allow testing the partner company incompatibility check
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'views/views.xml',
        'views/templates.xml',
    ],
    'demo': [
        'demo/demo.xml',
    ],
}