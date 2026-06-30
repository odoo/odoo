{
    'name': 'Survey CRM',
    'version': '1.0',
    'category': 'Marketing/Surveys',
    'summary': 'Generate leads from surveys',
    'description': """
    Bridge module between Survey and CRM.
    Enables the creation of a lead from a survey when the participant selects lead-generating answers.
    An option on the suggested answers can be activated to make them lead-generating.
    """,
    'depends': ['survey', 'crm'],
    'data': [
        'views/survey_question_views.xml',
        'views/survey_survey_views.xml',
        'views/survey_user_views.xml',
    ],
    'demo': [
        'demo/lead_qualification_survey_demo.xml',
        'demo/lead_qualification_answer_demo.xml',
    ],
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
