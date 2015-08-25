# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Recurring Documents',
    'version': '1.0',
    'category': 'Tools',
    'description': """
Create recurring documents.
===========================

This module allows to create new documents and add subscriptions on that document.

e.g. To have an invoice generated automatically periodically:
-------------------------------------------------------------
    * Define a document type based on Invoice object
    * Define a subscription whose source document is the document defined as
      above. Specify the interval information and partner to be invoice.
    """,
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'subscription_view.xml'
    ],
    'demo': ['subscription_demo.xml',],
    'installable': True,
    'auto_install': False,
}
