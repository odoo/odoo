# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Helpdesk After Sales',
    'category': 'Services/Helpdesk',
    'summary': 'Project, Tasks, After Sales',
    'depends': ['helpdesk', 'sale_management'],
    'auto_install': True,
    'description': """
Manage the after sale of the products from helpdesk tickets.
    """,
    'data': [
        'security/helpdesk_security.xml',
        'views/helpdesk_ticket_views.xml',
        'views/helpdesk_sla_views.xml',
    ],
    'demo': ['data/helpdesk_sale_demo.xml'],
    'license': 'OEEL-1',
}
