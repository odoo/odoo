# -*- coding: utf-8 -*-
{
    'name': 'Events Organization',
    'version': '1.7',
    'website': 'https://www.odoo.com/app/events',
    'category': 'Marketing/Events',
    'summary': 'Trainings, Conferences, Meetings, Exhibitions, Registrations',
    'description': """
Organization and management of Events.
======================================

The event module allows you to efficiently organize events and all related tasks: planning, registration tracking,
attendances, etc.

Key Features
------------
* Manage your Events and Registrations
* Use emails to automatically confirm and send acknowledgments for any event registration
""",
    'depends': ['base_setup', 'mail', 'phone_validation', 'portal', 'utm', 'barcodes'],
    'data': [
        'security/event_security.xml',
        'security/ir.model.access.csv',
        'views/event_menu_views.xml',
        'views/event_ticket_views.xml',
        'views/event_mail_views.xml',
        'views/event_registration_views.xml',
        'views/event_type_views.xml',
        'views/event_event_views.xml',
        'views/event_stage_views.xml',
        'report/event_event_templates.xml',
        'report/event_event_reports.xml',
        'data/ir_cron_data.xml',
        'data/mail_template_data.xml',
        'data/event_data.xml',
        'views/res_config_settings_views.xml',
        'views/event_templates.xml',
        'views/res_partner_views.xml',
        'views/event_tag_views.xml',
        'views/event_report_templates.xml',
    ],
    'demo': [
        'data/res_users_demo.xml',
        'data/res_partner_demo.xml',
        'data/event_demo_misc.xml',
        'data/event_demo.xml',
        'data/event_registration_demo.xml',
    ],
    'installable': True,
    'assets': {
        'web.assets_backend': [
            'event/static/src/client_action/event_barcode.js',
            'event/static/src/client_action/event_barcode.scss',
            'event/static/src/client_action/event_barcode.xml',
            'event/static/src/client_action/event_registration_summary_dialog.js',
            'event/static/src/client_action/event_registration_summary_dialog.xml',
            'event/static/src/scss/event.scss',
            'event/static/src/icon_selection_field/icon_selection_field.js',
            'event/static/src/icon_selection_field/icon_selection_field.xml',
            'event/static/src/js/tours/**/*',
        ],
        'web.assets_frontend': [
            'event/static/src/js/tours/**/*',
        ],
        'web.report_assets_common': [
            '/event/static/src/scss/event_foldable_badge_report.scss',
            '/event/static/src/scss/event_full_page_ticket_report.scss',
            '/event/static/src/scss/event_full_page_ticket_responsive_html_report.scss',
            '/event/static/src/scss/event_full_page_ticket_simplified_report.scss',
        ],
        'web.report_assets_pdf': [
            '/event/static/src/scss/event_full_page_ticket_report.scss',
            '/event/static/src/scss/event_full_page_ticket_report_pdf.scss',
        ],
    },
    'license': 'LGPL-3',
}
