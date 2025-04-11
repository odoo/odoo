{
    'name': 'Event Ticket Limiter',
    'description': """This module enforces a limit on the maximum number of tickets that can be booked in single registration.""",
    'category': 'Events',
    'license': 'LGPL-3',
    'depends': ['website_event'],
    'data': [
        'views/event_ticket_views.xml',
        'views/event_templates_page_registration.xml',
    ],
    'auto_install': True,
    'installable': True,
}
