# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': "Localization: Belgium",
    'summary': """Localization: Belgium""",
    'description': """This module allows us to load country specific data that
are used for specific localization like countries, country states or any other
country-related localization data that are not related to accounting. """,
    'category': 'Localization',
    'version': '1.0',
    'depends': [
        'base',
    ],
    'application': False,
    'installable': True,
    'auto_install': False,
    'data': [
        'data/res.country.state.csv',
    ],
}
