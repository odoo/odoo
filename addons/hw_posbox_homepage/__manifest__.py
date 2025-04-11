# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'IoT Box Homepage',
    'category': 'Sales/Point of Sale',
    'sequence': 6,
    'website': 'https://www.odoo.com/app/point-of-sale-hardware',
    'summary': 'A homepage for the IoT Box',
    'description': """
IoT Box Homepage
================

This module overrides Odoo web interface to display a simple
Homepage that explains what's the iotbox and shows the status,
and where to find documentation.

If you activate this module, you won't be able to access the 
regular Odoo interface anymore.

""",
    'assets': {
        'iot_homepage.assets': [  # dummy asset name to make sure it does not load outside of IoT homepage
            'hw_posbox_homepage/static/**/*',
        ],
    },
    'installable': False,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
