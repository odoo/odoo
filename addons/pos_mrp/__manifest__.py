# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'pos_mrp',
    'category': 'Sales/Point of Sale',
    'sequence': 6,
    'summary': 'Link module between Point of Sale and Mrp',
    'description': """
This is a link module between Point of Sale and Mrp.
""",
    'depends': ['point_of_sale', 'mrp'],
    'data': [
        'security/ir.access.csv',
    ],
    'assets': {
        'web.assets_tests': [
            'pos_mrp/static/tests/tours/**/*',
        ],
    },
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
