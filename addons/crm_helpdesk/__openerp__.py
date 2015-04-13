# -*- coding: utf-8 -*-

{
    'name': 'Helpdesk',
    'category': 'Customer Relationship Management', 
    'version': '1.0',
    'description': """
Helpdesk Management.
====================

Like records and processing of claims, Helpdesk and Support are good tools
to trace your interventions. This menu is more adapted to oral communication,
which is not necessarily related to a claim. Select a customer, add notes
and categorize your interventions with a channel and a priority level.
    """,
    'author': 'Odoo S.A.',
    'website': 'https://www.odoo.com',
    'depends': ['crm'],
    'data': [
        'views/crm_helpdesk_view.xml',
        'views/crm_helpdesk_menu.xml',
        'security/ir.model.access.csv',
        'report/crm_helpdesk_report_view.xml',
    ],
    'demo': ['data/crm_helpdesk_demo.xml'],
    'installable': True,
}
