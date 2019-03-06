# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Surveys',
    'version': '3.0',
    'category': 'Marketing',
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
    'depends': ['http_routing', 'mail'],
    'data': [
        'security/survey_security.xml',
        'security/ir.model.access.csv',
        'views/survey_views.xml',
        'views/survey_templates.xml',
        'views/survey_result.xml',
        'data/mail_template_data.xml',
        'wizard/survey_email_compose_message.xml',
        'data/survey_stages.xml',
    ],
    'demo': ['data/survey_demo_user.xml',
             'data/survey_demo_feedback.xml',
             'data/survey.user_input.csv',
             'data/survey.user_input_line.csv'],
    'installable': True,
    'auto_install': False,
    'application': True,
    'sequence': 105,
}
