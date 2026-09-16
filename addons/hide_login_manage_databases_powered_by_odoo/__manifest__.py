# -*- coding: utf-8 -*-
{
    'name': 'Hide Manage Databases & Hide Powered by Odoo',
    'version': '16.0.1.0.0',
    'sequence': 1,
    'summary': """
        Hide The Phrase Powered By Odoo located in the log in page,
    """,
    'description': "Hide login Manage Databases & Powered by Odoo Without installing website.",
    'author': 'Emad Al-Futahi',
    'maintainer': 'Emad Al-Futahi',
    'price': '0.0',
    'currency': 'USD',
    'license': 'LGPL-3',
    'depends': ['web']
    ,
    'data': [
        'views/login_templates.xml',
    ],
    'demo': [],
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': False,
    'auto_install': False,
}
