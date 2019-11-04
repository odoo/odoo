# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Members',
    'version': '1.0',
    'category': 'Sales/Sales',
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
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/membership_invoice_views.xml',
        'data/membership_data.xml',
        'views/product_views.xml',
        'views/partner_views.xml',
        'report/report_membership_views.xml',
    ],
    'website': 'https://www.odoo.com/page/community-builder',
}
