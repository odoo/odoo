# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Appointments',
    'version': '1.3',
    'category': 'Services/Appointment',
    'sequence': 215,
    'summary': 'Allow people to book meetings in your agenda',
    'website': 'https://www.odoo.com/app/appointments',
    'description': """
Allow clients to Schedule Appointments through the Portal
    """,
    'depends': ['calendar', 'onboarding', 'portal', 'resource', 'web_gantt'],
    'data': [
        'data/onboarding_data.xml',
        'data/calendar_data.xml',
        'data/mail_message_subtype_data.xml',
        'data/mail_template_data.xml',
        'data/resource_calendar_data.xml',
        'security/res_groups_data.xml',
        'security/ir_rule_data.xml',
        'security/ir.model.access.csv',
        'views/calendar_views.xml',
        'views/calendar_alarm_views.xml',
        'views/calendar_event_views.xml',
        'views/appointment_answer_input_views.xml',
        'views/appointment_invite_views.xml',
        'views/appointment_question_views.xml',
        'views/appointment_type_views.xml',
        'views/appointment_resource_views.xml',
        'views/appointment_slot_views.xml',
        'views/resource_calendar_leaves_views.xml',
        'views/appointment_menus.xml',
        'views/calendar_menus.xml',
        'views/appointment_templates_appointments.xml',
        'views/appointment_templates_registration.xml',
        'views/appointment_templates_validation.xml',
        'views/portal_templates.xml',
        'wizard/appointment_manage_leaves.xml',
        'wizard/appointment_onboarding_link.xml',
    ],
    'demo': [
        'data/res_partner_demo.xml',
        'data/appointment_type_demo.xml',
        'data/appointment_resource_demo.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'OEEL-1',
    'assets': {
        'web.assets_frontend': [
            'mail/static/src/js/utils.js',
            'appointment/static/src/js/utils.js',
            'appointment/static/src/scss/appointment.scss',
            'appointment/static/src/js/appointment_select_appointment_type.js',
            'appointment/static/src/js/appointment_select_appointment_slot.js',
            'appointment/static/src/js/appointment_validation.js',
            'appointment/static/src/js/appointment_form.js',
            'appointment/static/src/xml/*.xml',
        ],
        'web.assets_backend': [
            'appointment/static/src/scss/appointment_type_views.scss',
            'appointment/static/src/scss/web_calendar.scss',
            'appointment/static/src/views/**/*',
            'appointment/static/src/components/**/*',
            'appointment/static/src/js/appointment_insert_link_form_controller.js',
        ],
        'web_editor.backend_assets_wysiwyg': [
            'appointment/static/src/js/wysiwyg.js',
        ],
        'web.qunit_suite_tests': [
            'appointment/static/tests/*',
        ],
    }
}
