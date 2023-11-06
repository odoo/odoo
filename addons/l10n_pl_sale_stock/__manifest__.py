# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) 2009 - now Grzegorz Grzelak grzegorz.grzelak@openglobe.pl

{
    'name': 'Poland - Sales and Stock',
    'version': '2.0',
    'author': 'Odoo S.A.',
    'category': 'Accounting/Localizations',
    'description': """
        Bridge module to compute the Sale Date for the invoice when sale_stock is installed
    """,
    'depends': [
        'l10n_pl', 'sale_stock',
    ],
    'data': [
    ],
    'demo': [
    ],
    'auto_install': True,
    'license': 'LGPL-3',
}
