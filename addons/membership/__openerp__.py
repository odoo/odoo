# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Membership Management',
    'version': '0.1',
    'category': 'Association',
    'description': """
This module allows you to manage all operations for managing memberships.
=========================================================================

It supports different kind of members:
--------------------------------------
    * Free member
    * Associated member (e.g.: a group subscribes to a membership for all subsidiaries)
    * Paid members
    * Special member prices

It is integrated with sales and accounting to allow you to automatically
invoice and send propositions for membership renewal.
    """,
    'depends': ['base', 'product', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/membership_invoice_view.xml',
        'data/membership_data.xml',
        'views/membership_view.xml',
        'report/report_membership_view.xml',
    ],
    'demo': [
        'data/membership_demo.xml',
    
    ],
    'website': 'https://www.odoo.com/page/community-builder',
    'test': [
        '../account/test/account_minimal_test.xml'
    ],
    'installable': True,
}
