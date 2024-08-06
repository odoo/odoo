# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Indian - Sale Report(GST)',
    'version': '1.0',
    'description': """GST Sale Report""",
    'category': 'Accounting/Localizations/Sale',
    'depends': [
        'l10n_in',
        'sale',
    ],
    'data': [
        'views/report_sale_order.xml',
        'views/sale_views.xml',
        'views/res_partner_views.xml',
    ],
    'demo': [
        'data/product_demo.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': True,
    'license': 'LGPL-3',
}
