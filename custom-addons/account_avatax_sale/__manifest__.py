# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Avatax for SO',
    'version': '1.0',
    'category': 'Accounting/Accounting',
    'depends': ['sale_external_tax', 'account_avatax', 'sale'],
    'data': [
        'views/sale_order_views.xml',
        'reports/sale_order.xml',
    ],
    'auto_install': True,
    'license': 'OEEL-1',
}
