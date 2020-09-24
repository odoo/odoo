# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright 2015 Eezee-It

{
    'name': 'Worldline SIPS',
    'version': '1.1',
    'author': 'Eezee-It',
    'category': 'Accounting/Payment Acquirers',
    'sequence': 385,
    'description': """
Worldline SIPS Payment Acquirer for online payments

Implements the Worldline SIPS API for payment acquirers.
Other SIPS providers may be compatible, though this is
not guaranteed.""",
    'depends': ['payment'],
    'data': [
        'views/payment_views.xml',
        'views/payment_sips_templates.xml',
        'data/payment_acquirer_data.xml',
    ],
    'installable': True,
    'application': True,
    'post_init_hook': 'create_missing_journal_for_acquirers',
    'uninstall_hook': 'uninstall_hook',
}
