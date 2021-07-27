# -*- encoding: utf-8 -*-
{
    'name': 'Website - Sales Management',
    'version': '1.0',
    'category': 'Hidden',
    'description': """
Display orders to invoice in website dashboard.
""",
    'depends': [
        'sale_management',
        'website_sale',
    ],
    'installable': True,
    'auto_install': True,
    'data': [
    ],
    'demo': [
    ],
    'qweb': ['static/src/xml/*.xml'],
    'license': 'LGPL-3',
}
