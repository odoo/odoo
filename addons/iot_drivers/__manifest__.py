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
    'external_dependencies': [
        {'pypi': 'dbus-python', 'modules': ['dbus'], 'apt': 'python3-dbus'},
        {'pypi': 'netifaces', 'apt': 'python3-netifaces'},
        {'pypi': 'PyKCS11', 'apt': 'python3-pykcs11'},
        {'pypi': 'schedule', 'apt': 'python3-schedule'},
        {'pypi': 'websocket-client', 'modules': ['websocket'], 'apt': 'python3-websocket'},
        {'pypi': 'sentry-sdk', 'modules': ['sentry_sdk']},
        {'pypi': 'qrcode', 'apt': 'python3-qrcode'},
        {'pypi': 'pyserial', 'modules': ['serial'], 'apt': 'python3-serial'},
        {'pypi': 'pyusb', 'modules': ['usb'], 'apt': 'python3-usb'},
    ],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
