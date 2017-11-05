# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Indian - Sale Report(GST)',
    'version': '1.0',
    'description': """GST Sale Report""",
    'category': 'Localization',
    'depends': [
        'l10n_in',
        'sale',
    ],
    'data': [
        'views/report_sale_order.xml',
        'views/report_invoice_view.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': True,
}
