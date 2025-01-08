# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Events',
    'version': '1.4',
    'category': 'Marketing/Events',
    'sequence': 140,
    'summary': 'Publish events, sell tickets',
    'website': 'https://www.odoo.com/app/events',
    'depends': [
        'event',
        'website',
        'website_partner',
        'website_mail',
    ],
    'data': [
        'data/event_data.xml',
        'data/website_snippet_data.xml',
        'views/event_snippets.xml',
        'views/snippets/s_events.xml',
        'views/snippets/s_event_upcoming_snippet_preview_data.xml',
        'views/snippets/snippets.xml',
        'views/event_templates_list.xml',
        'views/event_templates_svg.xml',
        'views/event_templates_page.xml',
        'views/event_templates_page_registration.xml',
        'views/event_templates_page_misc.xml',
        'views/event_templates_widgets.xml',
        'views/event_event_views.xml',
        'views/event_registration_views.xml',
        'views/event_tag_category_views.xml',
        'views/event_tag_views.xml',
        'views/event_type_views.xml',
        'views/website_event_menu_views.xml',
        'views/website_visitor_views.xml',
        'views/event_menus.xml',
        'views/website_pages_views.xml',
        'views/event_event_add.xml',
        'security/ir.model.access.csv',
        'security/event_security.xml',
    ],
    'demo': [
        'data/res_partner_demo.xml',
        'data/event_demo.xml',
        'data/event_question_demo.xml',
        'data/event_registration_demo.xml',
        'data/event_registration_answer_demo.xml',
    ],
    'application': True,
    'assets': {
        'web.assets_backend': [
            'website_event/static/src/js/tours/**/*',
        ],
        'web.assets_tests': [
            'website_event/static/tests/tours/**/*',
        ],
        'web.assets_unit_tests': [
            'website_event/static/tests/interactions/**/*',
        ],
        'web.assets_unit_tests_setup': [
            'website_event/static/src/snippets/**/*.js',
            ('remove', 'website_event/static/src/snippets/**/options.js'),
        ],
        'web.assets_frontend': [
            'website_event/static/src/js/tours/**/*',
            'website_event/static/src/scss/event_templates_common.scss',
            'website_event/static/src/scss/event_templates_list.scss',
            'website_event/static/src/scss/event_templates_page.scss',
            'website_event/static/src/interactions/*.js',
        ],
        'website.assets_wysiwyg': [
            'website_event/static/src/snippets/s_events/options.js',
            'website_event/static/src/snippets/options.js',
        ],
        'website.assets_editor': [
            'website_event/static/src/js/systray_items/*.js',
        ],
    },
    'license': 'LGPL-3',
}
