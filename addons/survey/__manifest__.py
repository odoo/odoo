# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Surveys',
    'version': '3.0',
    'category': 'Marketing/Survey',
    'description': """
Create beautiful surveys and visualize answers
==============================================

It depends on the answers or reviews of some questions by different users. A
survey may have multiple pages. Each page may contain multiple questions and
each question may have multiple answers. Different users may give different
answers of question and according to that survey is done. Partners are also
sent mails with personal token for the invitation of the survey.
    """,
    'summary': 'Create surveys and analyze answers',
    'website': 'https://www.odoo.com/page/survey',
    'depends': [
        'auth_signup',
        'http_routing',
        'mail',
        'web_tour'],
    'data': [
        'views/survey_report_templates.xml',
        'views/survey_reports.xml',
        'data/mail_template_data.xml',
        'data/ir_actions_data.xml',
        'security/survey_security.xml',
        'security/ir.model.access.csv',
        'views/assets.xml',
        'views/survey_menus.xml',
        'views/survey_survey_views.xml',
        'views/survey_user_views.xml',
        'views/survey_question_views.xml',
        'views/survey_templates.xml',
        'wizard/survey_invite_views.xml',
    ],
    'demo': [
        'data/survey_demo_user.xml',
        'data/survey_demo_feedback.xml',
        'data/survey_demo_certification.xml',
        'data/survey.user_input_line.csv'
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'sequence': 105,
}
