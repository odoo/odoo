# -*- coding: utf-8 -*-

{
    'name': 'Questions on Events',
    'description': 'Questions on Events',
    'category': 'Marketing',
    'version': '1.0',
    'depends': ['website_event'],
    'data': [
        'views/website_event_questions_backend.xml',
        'views/website_event_questions_templates.xml',
        'report/report_event_question_view.xml',
        'security/ir.model.access.csv',
    ],
    'demo': [
        'data/demo.xml',
    ],
    'installable': True,
}
