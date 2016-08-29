# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Tax exigible',
    'version': '1.0',
    'category': 'Accounting',
    'description': """
    """,
    'depends': ['account_tax_cash_basis'],
    'data': [],
    'test': [],
    'demo': [],
    'auto_install': True,
    'installable': True,
    'post_init_hook': '_migration_script',
}
