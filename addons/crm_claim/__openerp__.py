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
        'crm_claim_view.xml',
        'crm_claim_menu.xml',
        'security/ir.model.access.csv',
        'report/crm_claim_report_view.xml',
        'crm_claim_data.xml',
        'res_partner_view.xml',
    ],
    'demo': ['crm_claim_demo.xml'],
    'test': [
        'test/process/claim.yml',
        'test/ui/claim_demo.yml'
    ],
    'installable': True,
    'auto_install': False,
}
