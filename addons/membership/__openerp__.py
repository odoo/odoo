# -*- coding: utf-8 -*-

{
    'name': 'Membership Management',
    'version': '1.0',
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
    'author': 'Odoo SA',
    'depends': ['base', 'product', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/membership_invoice_view.xml',
        'membership_view.xml',
        # 'report/report_membership_view.xml',
    ],
    'demo': [
        'membership_demo.xml',
        'membership_demo.yml'
    ],
    'website': 'https://www.odoo.com/page/community-builder',
    'test': ['test/test_membership.yml'],
    'installable': True,
    'images': [
        'images/members.jpeg',
        'images/membership_list.jpeg',
        'images/membership_products.jpeg'],
}
