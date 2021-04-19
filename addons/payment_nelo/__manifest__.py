# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Nelo Payment Acquirer',
    'category': 'Accounting/Payment Acquirers',
    'sequence': 345,
    'summary': 'Payment Acquirer: Nelo Implementation',
    'description': """Nelo Payment Acquirer""",
    'depends': ['payment'],
    'data': [
        'views/nelo_views.xml',
        'views/payment_nelo_templates.xml',
        'data/payment_acquirer_data.xml',
    ],
    'application': True,
    'post_init_hook': 'create_missing_journal_for_acquirers',
}
