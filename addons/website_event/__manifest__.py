# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Events',
    'version': '1.4',
    'category': 'Marketing/Events',
    'sequence': 140,
    'summary': 'Publish events, sell tickets',
    'website': 'https://www.odoo.com/app/events',
    'description': "",
    'depends': [
        'event',
        'website',
        'website_partner',
        'website_mail',
    ],
    'data': [
        'data/event_data.xml',
        'views/res_config_settings_views.xml',
        'views/event_snippets.xml',
        'views/event_templates_list.xml',
        'views/event_templates_page.xml',
        'views/event_templates_page_registration.xml',
        'views/event_templates_page_misc.xml',
        'views/event_templates_widgets.xml',
        'views/website_templates.xml',
        'views/event_event_views.xml',
        'views/event_registration_views.xml',
        'views/event_tag_category_views.xml',
        'views/event_type_views.xml',
        'views/website_event_menu_views.xml',
        'views/website_visitor_views.xml',
        'views/event_menus.xml',
        'security/ir.model.access.csv',
        'security/event_security.xml',
    ],
    'demo': [
        'data/res_partner_demo.xml',
        'data/website_visitor_demo.xml',
        'data/event_demo.xml',
        'data/event_registration_demo.xml',
    ],
    'application': True,
    'assets': {
        'web.assets_common': [
            'website_event/static/src/js/tours/**/*',
        ],
        'web.assets_tests': [
            'website_event/static/tests/**/*',
        ],
        'web.assets_frontend': [
            'website_event/static/src/scss/event_templates_common.scss',
            'website_event/static/src/scss/event_templates_list.scss',
            'website_event/static/src/scss/event_templates_page.scss',
            'website_event/static/src/snippets/s_country_events_list/000.scss',
            'website_event/static/src/js/display_timer_widget.js',
            'website_event/static/src/js/register_toaster_widget.js',
            'website_event/static/src/js/website_geolocation.js',
            'website_event/static/src/js/website_event.js',
            'website_event/static/src/js/website_event_ticket_details.js',
            'website_event/static/src/js/website_event_set_customize_options.js',
        ],
        'website.assets_editor': [
            'website_event/static/src/js/website_event.editor.js',
        ],
    },
    'license': 'LGPL-3',
}
