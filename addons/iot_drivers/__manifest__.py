# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Hardware Proxy',
    'category': 'Hidden',
    'sequence': 6,
    'summary': 'Connect the Web Client to Hardware Peripherals',
    'website': 'https://www.odoo.com/app/iot',
    'description': """
Hardware Poxy
=============

This module allows you to remotely use peripherals connected to this server.

This modules only contains the enabling framework. The actual devices drivers
are found in other modules that must be installed separately.

""",
    'assets': {
        'iot_drivers.assets': [  # dummy asset name to make sure it does not load outside of IoT homepage
            'iot_drivers/static/**/*',
        ],
    },
    'installable': False,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
