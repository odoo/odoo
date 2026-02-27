# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'POS Sunmi',
    'category': 'Sales/Point of Sale',
    'summary': 'Sunmi ePOS Printers in PoS',
    'description': """
Use Sunmi ePOS Printers without the IoT Box in the Point of Sale
""",
    'depends': ['point_of_sale'],
    'data': [
        'views/pos_printer.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_sunmi/static/lib/**/*',
            'pos_sunmi/static/src/**/*',
        ],
        'web.assets_backend': [
            'pos_sunmi/static/lib/**/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
