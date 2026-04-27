# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Meeting Rooms',
    'summary': 'Manage Meeting Rooms',
    'description': 'Experience the Ease of Booking Meeting Rooms with Real-Time Availability Display.',
    'category': 'Productivity/Room',
    'version': '1.0',
    'depends': ['mail', 'web_gantt'],
    'data': [
        'views/room_booking_views.xml',
        'views/room_room_views.xml',
        'views/room_menus.xml',
        'views/room_booking_templates_frontend.xml',
        'views/room_office_views.xml',
        'data/ir_module_category_data.xml',
        'security/ir_rule.xml',
        'security/ir.model.access.csv',
    ],
    'demo': [
        'demo/room_office.xml',
        'demo/room_room.xml',
        'demo/room_booking.xml',
    ],
    'installable': True,
    'application': True,
    'assets': {
        'web.assets_backend_lazy': [
            'room/static/src/room_booking_gantt_view/**/*',
        ],
        'web.qunit_suite_tests': [
            'room/static/tests/*.js',
            'room/static/src/room_booking/**/*.js',
            'room/static/src/room_booking/**/*.xml',
            'room/static/tests/room_booking_view_patch.xml',
        ],
        'room.assets_room_booking': [
            # 1 Define room variables (takes priority)
            "room/static/src/room_booking/primary_variables.scss",
            "room/static/src/room_booking/bootstrap_overridden.scss",

            #2 Load variables, Bootstrap and UI icons bundles
            ('include', 'web._assets_helpers'),
            ('include', 'web._assets_backend_helpers'),
            'web/static/src/scss/pre_variables.scss',
            'web/static/lib/bootstrap/scss/_variables.scss',
            'web/static/lib/bootstrap/scss/_variables-dark.scss',
            'web/static/lib/bootstrap/scss/_maps.scss',
            ('include', 'web._assets_bootstrap_backend'),
            "web/static/src/libs/fontawesome/css/font-awesome.css",
            "web/static/lib/odoo_ui_icons/*",
            'web/static/src/legacy/scss/ui.scss',
            'web/static/src/scss/base_frontend.scss',
            'web/static/src/core/utils/transitions.scss',
            'web/static/src/core/notifications/notification.scss',
            'web/static/src/core/ui/block_ui.scss',

            # Room's specific assets
            'room/static/src/room_booking/**/*',
        ],
    },
    'license': 'OEEL-1',
}
