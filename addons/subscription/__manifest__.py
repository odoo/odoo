# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Recurring Documents',
    'category': 'Extra Tools',
    'description': """
Create recurring documents.
===========================

This module allows to create new documents and add subscriptions on that document.

e.g. To have an invoice generated automatically periodically:
-------------------------------------------------------------
    * Define a document type based on Invoice object
    * Define a subscription whose source document is the document defined as
      above. Specify the interval information and partner to be invoiced.
    """,
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/subscription_view.xml'
    ],
    'demo': ['data/subscription_demo.xml'],
}
