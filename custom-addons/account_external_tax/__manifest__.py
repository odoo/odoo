# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': '3rd Party Tax Calculation',
    'description': '''
3rd Party Tax Calculation
=========================

Provides a common interface to be used when implementing apps to outsource tax calculation.
    ''',
    'version': '1.0',
    'category': 'Accounting/Accounting',
    'depends': ['account', 'payment'],  # payment because of the payment.link.wizard inherit
    'data': [
        'views/account_move_views.xml',
    ],
    'license': 'OEEL-1',
}
