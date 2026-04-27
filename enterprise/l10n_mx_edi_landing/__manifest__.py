# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Odoo Mexico Localization for Stock/Landing',
    'countries': ['mx'],
    'summary': 'Generate Electronic Invoice with custom numbers',
    'version': '1.0',
    'category': 'Accounting/Localizations/EDI',
    'depends': [
        'stock_landed_costs',
        'sale_management',
        'sale_stock',
        'l10n_mx_edi_extended',
    ],
    'data': [
        'views/stock_landed_cost.xml',
    ],
    'installable': True,
    'license': 'OEEL-1',
}
