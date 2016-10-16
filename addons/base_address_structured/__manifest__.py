# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Structured Addresses',
    'summary': 'Split street in several fields',
    'sequence': '19',
    'category': 'Base',
    'complexity': 'easy',
    'description': """
Split Addresses
===============

For legal reports, some countries need to split the street into several fields,
with the street name, the house number, and room number. This module also
replace the city by a relation field.
        """,
    'data': [
        'views/base_address_structured.xml'
    ],
    'depends': ['base'],
}
