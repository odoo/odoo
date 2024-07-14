# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Helpdesk Mail Plugin',
    'category': 'Services/Helpdesk',
    'depends': ['helpdesk', 'mail_plugin'],
    'auto_install': True,
    'version': '1.0',
    'summary': 'Convert emails to Helpdesk Tickets.',
    'description': """Integrate helpdesk with your mailbox.
                   Turn emails received in your mailbox into Tickets and log their content as internal notes.""",
    'data': [
        'views/helpdesk_ticket_views.xml'
    ],
    'license': 'OEEL-1',
}
