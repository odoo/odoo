# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Allow custom taxes in POS",
    'category': 'Accounting/Accounting',
    'version': '1.0',
    'description': """Add code to manage custom taxes to the POS assets bundle""",
    'depends': ['account_tax_python', 'point_of_sale'],
    'assets': {
        'point_of_sale._assets_pos': [
            'account_tax_python/static/src/helpers/*.js',
        ],
    },
    'auto_install': True,
    'license': 'LGPL-3',
}
