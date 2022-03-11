# Part of Odoo. See LICENSE file for full copyright and licensing details.
# Original Copyright 2015 Eezee-It, modified and maintained by Odoo.

{
    'name': 'On site payment',
    'version': '1.0',
    'category': 'Accounting/Payment Acquirers',
    'description': """
Payment acquirer for on site payment. This allows customers to pay for their orders directly in one of
your point of sales""",
    'depends': ['payment', 'point_of_sale', 'delivery'],
    'data': [
        'data/pos_onsite.xml'
    ],
    'application': False,
    'auto_install': True,
    'license': 'LGPL-3',
}
