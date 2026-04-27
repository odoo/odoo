# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Point of Sale Restaurant Appointment',
    'version': '1.0',
    'category': 'Sales/Point of Sale',
    'sequence': 6,
    'summary': 'This module lets you manage online reservations for restaurant tables',
    'website': 'https://www.odoo.com/app/appointments',
    'depends': ['appointment', 'pos_restaurant'],
    'data': [
        'views/calendar_event_views.xml',
        'views/pos_restaurant_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'demo': [
        'demo/pos_restaurant_appointment_demo.xml',
    ],
    'license': 'OEEL-1',
    'post_init_hook': '_pos_restaurant_appointment_after_init',
    'assets': {
        # Having the editor add a lot of files to the PoS bundle.
        # We can maybe find a way to have a "light editor" with smaller bundle
        'pos_restaurant_appointment.html_editor': [
            "html_editor/static/src/utils/*.js",
            ("remove", "html_editor/static/src/utils/list.js"),
            ("remove", "html_editor/static/src/utils/regex.js"),

            'html_editor/static/src/plugin.js',
            'html_editor/static/src/plugin_sets.js',
            'html_editor/static/src/wysiwyg.js',
            'html_editor/static/src/wysiwyg.xml',
            'html_editor/static/src/position_hook.js',
            'html_editor/static/src/dropdown_autovisibility_hook.js',
            'html_editor/static/src/local_overlay_container.js',
            'html_editor/static/src/local_overlay_container.xml',
            'html_editor/static/src/html_migrations/**/*',
            'html_editor/static/src/core/**/*',
            'html_editor/static/src/main/**/*',
            'html_editor/static/src/fields/**/*',
            'html_editor/static/src/others/**/*',
            'html_editor/static/src/editor.js',

            'web/static/lib/dompurify/DOMpurify.js',
        ],

        'point_of_sale._assets_pos': [
            ('include', 'pos_restaurant_appointment.html_editor'),
            'web_gantt/static/src/**/*',
            'pos_restaurant_appointment/static/src/**/*',
            'appointment/static/src/views/gantt/**/*',
            'calendar/static/src/views/widgets/**/*',
            'calendar/static/src/views/calendar_form/**/*',
            ('remove', 'web_gantt/static/src/**/*.dark.scss'),
        ],
    'web.assets_tests': [
            'pos_restaurant_appointment/static/tests/tours/**/*',
        ],
    }
}
