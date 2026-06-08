# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'POS iMin',
    'category': 'Sales/Point of Sale',
    'sequence': 6,
    'summary': 'iMin ePOS Printers in PoS',
    'description': """

Use iMin ePOS Printers without the IoT Box in the Point of Sale
""",
    'depends': ['point_of_sale'],
    'data': [
        'views/pos_printer_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_imin/static/lib/**/*',
            'pos_imin/static/src/**/*',
            ('remove', 'pos_imin/static/src/backend/**/*'),
        ],
        'web.assets_backend': [
            'pos_imin/static/lib/**/*',
            'pos_imin/static/src/backend/test_imin/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
