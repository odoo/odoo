# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Account Customer Portal',
    'category': 'Website',
    'summary': 'Add your accounting document in the frontend portal',
    'version': '1.0',
    'description': """
Add your accounting document in the frontend portal. Give customers the list and the state of their invoices.
        """,
    'depends': [
        'account',
        'website_portal',
        'website_payment',
    ],
    'data': [
    ],
    'demo': [],
    'installable': True,
}
