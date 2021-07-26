# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'PayuLatam Payment Acquirer',
    'category': 'Accounting/Payment Acquirers',
    'sequence': 370,
    'summary': 'Payment Acquirer: PayuLatam Implementation',
    'description': """Payulatam payment acquirer""",
    'depends': ['payment'],
    'data': [
        'views/payment_views.xml',
        'views/payment_payulatam_templates.xml',
        'data/payment_acquirer_data.xml',
    ],
    'application': True,
    'post_init_hook': 'create_missing_journal_for_acquirers',
    'license': 'LGPL-3',
}
