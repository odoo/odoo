# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Google Users',
    'category': 'Tools',
    'description': """
The module adds google user in res user.
========================================
""",
    'depends': ['base_setup'],
    'data': [
        'data/google_account_data.xml',
    ],
    'license': 'LGPL-3',
}
