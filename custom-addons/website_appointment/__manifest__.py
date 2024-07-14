# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Website Appointments',
    'version': '1.0',
    'category': 'Services/Appointment',
    'sequence': 215,
    'website': 'https://www.odoo.com/app/appointments',
    'description': """
Allow clients to Schedule Appointments through your Website
-------------------------------------------------------------

""",
    'depends': ['appointment', 'website_enterprise', 'website_partner'],
    'data': [
        'data/calendar_data.xml',
        'data/website_data.xml',
        'views/appointment_type_views.xml',
        'views/appointment_invite_views.xml',
        'views/calendar_menus.xml',
        'views/appointment_templates_appointments.xml',
        'views/appointment_templates_registration.xml',
        'views/appointment_templates_validation.xml',
        'views/website_pages_views.xml',
        'views/snippets/s_online_appointment.xml',
        'views/snippets/s_searchbar.xml',
        'views/snippets/snippets.xml',
        'security/calendar_security.xml',
        'security/ir.model.access.csv',
    ],
    'demo': [
        'data/appointment_demo.xml',
    ],
    'installable': True,
    'auto_install': ['appointment', 'website_enterprise'],
    'license': 'OEEL-1',
    'assets': {
        'web.assets_tests': [
            'website_appointment/static/tests/tours/*',
        ],
        'web.assets_frontend': [
            'website_appointment/static/src/scss/website_appointment.scss',
            'website_appointment/static/src/scss/website_appointment_editor.scss',
            'website_appointment/static/src/xml/website_appointment_templates.xml',
            'website_appointment/static/src/xml/appointment_no_slot.xml',
        ],
        'website.assets_editor': [
            'website_appointment/static/src/js/systray_items/*.js',
        ],
        'website.assets_wysiwyg': [
            'website_appointment/static/src/snippets/s_online_appointment/options.js',
        ],
    }
}
