# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Denmark - UNSPSC product code',
    'countries': ['dk'],
    'version': '1.0',
    'author': 'Odoo Sa',
    'category': 'Accounting/Localizations/EDI',
    'description': "UNSPSC product code dependencies for Denmark",
    'depends': ['l10n_dk', 'account_edi', 'product_unspsc'],
    'auto_install': ['l10n_dk', 'product_unspsc'],
    'installable': True,
    'license': 'OEEL-1',
}
