# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'City Timezones',
    'summary': 'Cities of more than 15 000 inhabitants with their timezone and coordinates',
    'category': 'Hidden/Tools',
    'description': """
City Timezones
==============

Loads the cities of more than 15 000 inhabitants from GeoNames (cities15000)
into the list of cities, with their timezone and coordinates.

Cities already provided by a localization are completed instead of duplicated
when they can be matched unambiguously.

Data: GeoNames (https://www.geonames.org), licensed under CC BY 4.0.
    """,
    'depends': ['base_address_extended'],
    'data': [
        'views/res_city_views.xml',
    ],
    'post_init_hook': '_load_geonames_cities',
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
