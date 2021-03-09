# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Surveys',
    'version': '3.3',
    'category': 'Marketing/Surveys',
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
        'web_tour',
        'gamification'],
    'data': [
        'views/survey_report_templates.xml',
        'views/survey_reports.xml',
        'data/mail_template_data.xml',
        'data/ir_actions_data.xml',
        'security/survey_security.xml',
        'security/ir.model.access.csv',
        'views/survey_menus.xml',
        'views/survey_survey_views.xml',
        'views/survey_user_views.xml',
        'views/survey_question_views.xml',
        'views/survey_templates.xml',
        'views/survey_templates_management.xml',
        'views/survey_templates_print.xml',
        'views/survey_templates_statistics.xml',
        'views/survey_templates_user_input_session.xml',
        'views/gamification_badge_views.xml',
        'wizard/survey_invite_views.xml',
        'views/res_partner_views.xml',
    ],
    'demo': [
        'data/survey_demo_user.xml',
        'data/survey_demo_feedback.xml',
        'data/survey_demo_certification.xml',
        'data/survey_demo_quiz.xml',
        'data/survey_demo_quiz_userinput.xml',
        'data/survey_demo_conditional.xml',
        'data/survey.user_input.line.csv'
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'sequence': 220,
    'assets': {
        'survey.survey_assets': [
            # new asset template 
            'web/static/lib/Chart/Chart.js',
            # new asset template 
            'web/static/src/js/fields/field_utils.js',
            # new asset template 
            'survey/static/src/js/survey_quick_access.js',
            # new asset template 
            'survey/static/src/js/survey_timer.js',
            # new asset template 
            'survey/static/src/js/survey_breadcrumb.js',
            # new asset template 
            'survey/static/src/js/survey_form.js',
            # new asset template 
            'survey/static/src/js/survey_print.js',
            # new asset template 
            'survey/static/src/js/survey_result.js',
            # None None
            ('include', 'web._assets_helpers'),
            # None None
            ('include', 'web._assets_frontend_helpers'),
            # new asset template 
            'web/static/lib/bootstrap/scss/_variables.scss',
            # new asset template 
            'survey/static/src/css/survey_print.css',
            # new asset template 
            'survey/static/src/css/survey_result.css',
            # new asset template 
            'survey/static/src/scss/survey_form.scss',
        ],
        'survey.survey_user_input_session_assets': [
            # new asset template 
            'survey/static/src/js/libs/chartjs-plugin-datalabels.min.js',
            # new asset template 
            'survey/static/src/js/survey_session_colors.js',
            # new asset template 
            'survey/static/src/js/survey_session_chart.js',
            # new asset template 
            'survey/static/src/js/survey_session_text_answers.js',
            # new asset template 
            'survey/static/src/js/survey_session_leaderboard.js',
            # new asset template 
            'survey/static/src/js/survey_session_manage.js',
        ],
        'web.report_assets_pdf': [
            # after link[last()]
            'survey/static/src/scss/survey_reports.scss',
        ],
        'web.assets_backend': [
            # inside .
            'survey/static/src/css/survey_result.css',
            # inside .
            'survey/static/src/js/fields_section_one2many.js',
            # inside .
            'survey/static/src/js/fields_form_page_description.js',
            # after link[last()]
            'survey/static/src/scss/survey_views.scss',
        ],
        'web.assets_tests': [
            # inside .
            'survey/static/tests/tours/certification_failure.js',
            # inside .
            'survey/static/tests/tours/certification_success.js',
            # inside .
            'survey/static/tests/tours/survey.js',
            # inside .
            'survey/static/tests/tours/survey_prefill.js',
            # inside .
            'survey/static/tests/tours/survey_tour_session_tools.js',
            # inside .
            'survey/static/tests/tours/survey_tour_session_create.js',
            # inside .
            'survey/static/tests/tours/survey_tour_session_start.js',
            # inside .
            'survey/static/tests/tours/survey_tour_session_manage.js',
            # inside .
            'survey/static/tests/tours/survey_session_manage_test.js',
        ],
    }
}
