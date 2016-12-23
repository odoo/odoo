# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'City Addresses',
    'summary': 'Add a many2one field city on addresses',
    'sequence': '19',
    'category': 'Base',
    'complexity': 'easy',
    'description': """
City Management in Addresses
============================

This module allows to enforce users to choose the city of a partner inside a given list instead of a free text field.
        """,
    'data': [
        'security/ir.model.access.csv',
        'views/res_city_view.xml',
        'views/res_country_view.xml',
    ],
    'depends': ['base'],
}
