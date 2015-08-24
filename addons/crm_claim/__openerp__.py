# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Claims Management',
    'version': '1.0',
    'category': 'Customer Relationship Management',
    'description': """

Manage Customer Claims.
=======================
This application allows you to track your customers/vendors claims and grievances.

It is fully integrated with the email gateway so that you can create
automatically new claims based on incoming emails.
    """,
    'depends': ['crm'],
    'data': [
        'security/ir.model.access.csv',
        'data/crm_claim_data.xml',
        'views/crm_claim_views.xml',
        'views/crm_claim_menu.xml',
        'views/res_partner_views.xml',
        'views/crm_claim_report_views.xml',
    ],
    'demo': ['data/crm_claim_demo.xml'],
    'test': [
        'tests/process/claim.yml',
        'tests/ui/claim_demo.yml'
    ],
    'installable': True,
}
