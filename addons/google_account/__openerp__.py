# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Google Users',
    'version': '1.0',
    'category': 'Extra Tools',
    'description': """
The module adds google user in res user.
========================================
""",
    'depends': ['base_setup'],
    'data': [
        'google_account_data.xml',
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
}
