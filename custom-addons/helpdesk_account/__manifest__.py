# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Helpdesk Account',
    'category': 'Services/Helpdesk',
    'summary': 'Project, Tasks, Account',
    'depends': ['helpdesk_sale', 'account'],
    'description': """
Create Credit Notes from Helpdesk tickets
    """,
    'data': [
        'data/mail_message_subtype_data.xml',
        'wizard/account_move_reversal_views.xml',
        'views/helpdesk_ticket_views.xml',
    ],
    'demo': [
       'data/helpdesk_account_demo.xml'
    ],
    'license': 'OEEL-1',
}
