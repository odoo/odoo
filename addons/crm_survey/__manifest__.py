{
    'name': 'Lead from Survey',
    'version': '1.0',
    'category': 'Sales/CRM',
    'summary': 'Generate lead from survey',
    'description': """
    Bridge module between CRM and survey.
    Enables the creation of a survey when the participant selects lead-generating answers.
    An option on the suggested answers can be activated to make them lead-generating.
    """,
    'depends': ['crm', 'survey'],
    'data': [
        'views/survey_question_views.xml',
        'views/survey_survey_views.xml',
    ],
    'demo': [
        'demo/lead_qualification_survey_demo.xml',
        'demo/lead_qualification_answer_demo.xml',
    ],
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
