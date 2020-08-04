# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Indian - Purchase Report(GST)',
    'version': '1.0',
    'description': """GST Purchase Report""",
    'category': 'Accounting/Localizations/Purchase',
    'depends': [
        'l10n_in',
        'purchase',
    ],
    'data': [
        'views/report_purchase_order.xml',
        'views/purchase_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': True,
}
