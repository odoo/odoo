# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Pay to Book on Website',
    'version': '1.0',
    'category': 'Hidden',
    'summary': 'Up-front payment on bookings on website',
    'description': """Add a payment step at the end of appointment and resource bookings, on website""",
    'license': 'OEEL-1',
    'auto_install': True,
    'depends': ['appointment_account_payment', 'website_enterprise', 'website_appointment'],
    'demo': [
        'data/appointment_demo.xml',
    ],
    'data': [
        'views/appointment_templates_appointments.xml',
        'views/appointment_templates_payment.xml',
        'views/calendar_booking_templates.xml',
    ]
}
