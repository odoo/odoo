# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Surveys',
    'version': '3.5',
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
    'summary': 'Send your surveys or share them live.',
    'website': 'https://www.odoo.com/app/surveys',
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
        'data/gamification_badge_demo.xml',
        'data/res_users_demo.xml',
        'data/survey_demo_feedback.xml',
        'data/survey_demo_feedback_user_input.xml',
        'data/survey_demo_feedback_user_input_line.xml',
        'data/survey_demo_certification.xml',
        'data/survey_demo_certification_user_input.xml',
        'data/survey_demo_certification_user_input_line.xml',
        'data/survey_demo_quiz.xml',
        'data/survey_demo_quiz_user_input.xml',
        'data/survey_demo_quiz_user_input_line.xml',
        'data/survey_demo_conditional.xml',
    ],
    'installable': True,
    'application': True,
    'sequence': 220,
    'assets': {
        'survey.survey_assets': [
            'web/static/lib/Chart/Chart.js',
            'survey/static/src/js/survey_image_zoomer.js',
            'survey/static/src/js/survey_quick_access.js',
            'survey/static/src/js/survey_timer.js',
            'survey/static/src/js/survey_breadcrumb.js',
            'survey/static/src/js/survey_form.js',
            'survey/static/src/js/survey_preload_image_mixin.js',
            'survey/static/src/js/survey_print.js',
            'survey/static/src/js/survey_result.js',
            ('include', 'web._assets_helpers'),
            ('include', 'web._assets_frontend_helpers'),
            'web/static/src/libs/bootstrap/pre_variables.scss',
            'web/static/lib/bootstrap/scss/_variables.scss',
            'survey/static/src/scss/survey_templates_form.scss',
            'survey/static/src/scss/survey_templates_results.scss',
        ],
        'survey.survey_user_input_session_assets': [
            'survey/static/src/js/libs/chartjs-plugin-datalabels.min.js',
            'survey/static/src/js/survey_session_colors.js',
            'survey/static/src/js/survey_session_chart.js',
            'survey/static/src/js/survey_session_text_answers.js',
            'survey/static/src/js/survey_session_leaderboard.js',
            'survey/static/src/js/survey_session_manage.js',
        ],
        'web.report_assets_common': [
            'survey/static/src/scss/survey_reports.scss',
        ],
        'web.assets_backend': [
            'survey/static/src/question_page/*.js',
            'survey/static/src/js/fields_section_one2many.js',
            'survey/static/src/js/fields_form_page_description.js',
            'survey/static/src/js/survey_renderers.js',
            'survey/static/src/js/survey_views.js',
            'survey/static/src/scss/survey_survey_views.scss',
            'survey/static/src/scss/survey_question_views.scss',
            'survey/static/src/scss/survey_templates_results.scss',
        ],
        'web.assets_tests': [
            'survey/static/tests/tours/*.js',
        ],
        'web.qunit_suite_tests': [
            'survey/static/tests/components/*.js',
        ],
        'web.assets_common': [
            'survey/static/src/js/tours/survey_tour.js',
        ],
        'web.assets_qweb': [
            'survey/static/src/question_page/*.xml',
        ],
    },
    'license': 'LGPL-3',
}
