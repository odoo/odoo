# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Pay to Book with eCommerce",
    'version': '1.0',
    'category': 'Hidden',
    'summary': "eCommerce on appointments",
    'description': """Enable a payment step to your bookings, using the e-commerce features of the website.""",
    'license': 'OEEL-1',
    'auto_install': True,
    'depends': ['website_appointment_account_payment', 'website_sale'],
    'data': [
        'views/appointment_templates_appointments.xml',
        'views/calendar_booking_views.xml',
        'views/calendar_event_views.xml',
        'views/sale_order_views.xml',
        'views/website_sale_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'website_appointment_sale/static/src/scss/website_appointment_sale.scss',
            'website_appointment_sale/static/src/js/appointment_sale_confirmation.js',
        ],
    },
}
