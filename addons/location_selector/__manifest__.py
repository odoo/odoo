# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Location Selector',
    'version': '1.0',
    'category': 'LocationSelector',
    'sequence': 5,
    'summary': 'Location selector component.',
    'description': "Allow choosing and displaying saved addresses.",
    'depends': [
        'web',
    ],
    'assets': {
        'web.assets_frontend': [
            'location_selector/static/src/**/*',
        ],
        'web.assets_unit_tests_setup': [
            'location_selector/static/src/**/*',
        ],
    },
    'installable': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
