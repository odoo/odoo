# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'Remove Powered By Odoo',
    'version' : '16.0.2',
    'summary': """ 
        Remove powered by odoo, Remove powered by odoo from login page, remove powered by from signup page, remove powered by odoo login screen,
        Hide powered by odoo, odoo powered by hide, odoo powered by remove, disable powered by odoo login screen
    """,
    'sequence': 10,
    'description': """
        Remove Powered by Odoo from login screen
    """,
    'category': 'Extra Tools',
    'author': 'A Cloud ERP',
    'website': 'https://www.aclouderp.com',
    'images' : ['static/description/powered_by_odoo.png'],
    'depends' : ['base'],
    'data': [
        'views/web_login.xml',
    ],
    'demo': [
    ],
    'installable': True,
    'application': True,
    'assets': {
        'web._assets_primary_variables': [
        ],
        'web.assets_backend': [

        ],
        'web.assets_frontend': [
        ],
        'web.assets_tests': [
        ],
        'web.qunit_suite_tests': [
        ],
    },
    'license': 'LGPL-3',
}
