# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'CCAvenue Payment Acquirer',
    'category': 'Accounting',
    'summary': 'Payment Acquirer: CCAvenue Implementation',
    'description': """CCAvenue Payment Acquirer""",
    'depends': ['payment'],
    'external_dependencies': {'python': ['Crypto']},
    'data': [
        'views/payment_acquirer.xml',
        'views/payment_ccavenue_templates.xml',
        'data/payment_ccavenue_data.xml',
    ],
    'post_init_hook': 'create_missing_journal_for_acquirers',
}
