# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Extended Addresses',
    'summary': 'Add extra fields on addresses',
    'sequence': 19,
    'version': '1.1',
    'category': 'Sales/Sales',
    'description': """
Extended Addresses Management
=============================

This module provides the ability to choose a city from a list (in specific countries).

It is primarily used for EDIs that might need a special city code.
        """,
    'data': [
        'views/res_city_view.xml',
        'views/res_country_view.xml',
        'views/res_partner_views.xml',
        'security/ir.access.csv',
    ],
    'depends': ['web'],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
