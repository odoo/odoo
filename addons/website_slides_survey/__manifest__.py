# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Course Certifications",
    'summary': 'Add certification capabilities to your courses',
    'description': """This module lets you use the full power of certifications within your courses.""",
    'category': 'Website/eLearning',
    'version': '1.0',
    'depends': ['website_slides', 'survey'],
    'installable': True,
    'auto_install': True,
    'data': [
        'security/ir.model.access.csv',
        'views/slide_channel_views.xml',
        'views/slide_slide_views.xml',
        'views/survey_survey_views.xml',
        'views/website_slides_menu_views.xml',
        'views/website_slides_templates_course.xml',
        'views/website_slides_templates_lesson.xml',
        'views/website_slides_templates_lesson_fullscreen.xml',
        'views/website_slides_templates_homepage.xml',
        'views/survey_templates.xml',
        'views/website_profile.xml',
        'data/mail_template_data.xml',
        'data/gamification_data.xml',
    ],
    'demo': [
        'data/survey_demo.xml',
        'data/slide_slide_demo.xml',
        'data/survey.user_input.line.csv',
    ],
    'assets': {
        'web.assets_frontend': [
            'website_slides_survey/static/src/scss/website_slides_survey.scss',
            'website_slides_survey/static/src/js/slides_upload.js',
            'website_slides_survey/static/src/js/slides_course_fullscreen_player.js',
            'website_slides_survey/static/src/js/slides_certification_upload_toast.js',
        ],
        'survey.survey_assets': [
            'website_slides_survey/static/src/scss/website_slides_survey_result.scss',
        ],
    },
    'license': 'LGPL-3',
}
