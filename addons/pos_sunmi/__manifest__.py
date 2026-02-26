# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'POS Sunmi',
    'version': '1.0',
    'category': 'Sales/Point of Sale',
    'summary': 'Sunmi ePOS Printers in PoS',
    'description': """
Use Sunmi ePOS Printers without the IoT Box in the Point of Sale
""",
    'depends': ['point_of_sale'],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_sunmi/static/lib/**/*',
            'pos_sunmi/static/src/**/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
