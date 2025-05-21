# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Stock Test',
    'version': '1.0',
    'category': 'Hidden/Tests',
    'summary': 'Stock tests module for tests needing speficic data',
    'description': "Stock tests module for tests needing speficic data",
    'depends': ['stock'],
    'data': [
        'data/test_stock_data.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}
