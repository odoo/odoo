# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Events Product',
    'version': '1.0',
    'category': 'Marketing/Events',
    'depends': ['event'],
    'data': [
        'views/event_event_views.xml',
        'views/event_question_views.xml',
        'views/event_registration_answer_views.xml',
        'views/event_registration_views.xml',
        'views/event_type_views.xml',
        'data/event_demo.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'auto_install': True,
    'assets': {},
    'license': 'LGPL-3',
}
