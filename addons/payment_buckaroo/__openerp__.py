# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Buckaroo Payment Acquirer',
    'category': 'Hidden',
    'summary': 'Payment Acquirer: Buckaroo Implementation',
    'description': """Buckaroo Payment Acquirer""",
    'depends': ['payment'],
    'data': [
        'views/buckaroo_templates.xml',
        'views/payment_acquirer.xml',
        'data/buckaroo_data.xml',
    ],
}
