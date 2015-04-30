# -*- coding: utf-8 -*-

{
    'name': 'Claims Management',
    'version': '1.0',
    'category': 'Customer Relationship Management',
    'description': """

Manage Customer Claims.
=======================
This application allows you to track your customers/suppliers claims and grievances.

It is fully integrated with the email gateway so that you can create
automatically new claims based on incoming emails.
    """,
    'author': 'Odoo SA',
    'website': 'https://www.odoo.com',
    'depends': ['crm'],
    'data': [
        'views/crm_claim_view.xml',
        'views/crm_claim_menu.xml',
        'views/res_partner_view.xml',
        'security/ir.model.access.csv',
        'report/crm_claim_report_view.xml',
        'data/crm_claim_data.xml',
    ],
    'demo': ['data/crm_claim_demo.xml'],
    'installable': True,
}
