# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Extended Addresses',
    'summary': 'Add extra fields on addresses',
    'sequence': '19',
    'category': 'Hidden',
    'complexity': 'easy',
    'description': """
Extended Addresses Management
=============================

This module holds all extra fields one may need to manage accurately addresses.

For example, in legal reports, some countries need to split the street into several fields,
with the street name, the house number, and room number.
        """,
    'data': [
        'views/base_address_extended.xml',
        'data/base_address_extended_data.xml',
    ],
    'depends': ['base'],
    'post_init_hook': '_update_street_format',
    'license': 'LGPL-3',
}
