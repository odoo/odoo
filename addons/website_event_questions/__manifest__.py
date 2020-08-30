# -*- coding: utf-8 -*-

{
    'name': 'Questions on Events',
    'description': 'Questions on Events',
    'category': 'Marketing',
    'version': '1.1',
    'depends': ['website_event'],
    'data': [
        'views/assets.xml',
        'views/event_views.xml',
        'views/event_registration_answer_views.xml',
        'views/event_registration_views.xml',
        'views/event_question_views.xml',
        'views/event_templates.xml',
        'security/security.xml',
        'security/ir.model.access.csv',
    ],
    'demo': [
        'data/event_question_demo.xml',
        'data/event_demo.xml',
        'data/event_registration_demo.xml',
    ],
    'installable': True,
}
