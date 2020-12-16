# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Odoo Payments by Adyen Payment Acquirer',
    'category': 'Accounting/Payment Acquirers',
    'sequence': 330,
    'summary': 'Payment Acquirer: Odoo Payments by Adyen',
    'version': '1.0',
    'description': """Odoo Payments by Adyen""",
    'depends': ['payment', 'adyen_platforms'],
    'data': [
        'views/payment_views.xml',
        'views/payment_odoo_by_adyen_templates.xml',
        'data/payment_acquirer_data.xml',
    ],
    'installable': True,
    'application': True,
}
