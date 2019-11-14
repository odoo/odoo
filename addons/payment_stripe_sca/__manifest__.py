# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Stripe Payment Acquirer - Strong Customer Authentication Update',
    'category': 'Hidden',
    'summary': 'Payment Acquirer: Stripe Implementation for the EU PSD2',
    'version': '1.0',
    'description': """Stripe Payment Acquirer - Strong Customer Authentication Update""",
    'depends': ['payment_stripe'],
    'auto_install': True,
    'data': [
        'views/assets.xml',
        'views/payment_templates.xml',
    ],
    'images': ['static/description/icon.png'],
}
