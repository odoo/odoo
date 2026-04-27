# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details
{
    'name': "Helpdesk FSM Reports",
    'summary': "Worksheet template when planning an intervention",
    'description': """
Display the worksheet template when planning an Intervention from a ticket
    """,
    'category': 'Services/Helpdesk',
    'depends': ['helpdesk_fsm', 'industry_fsm_report'],
    'data': [
        'wizard/create_task_views.xml',
    ],
    'auto_install': True,
    'license': 'OEEL-1',
}
