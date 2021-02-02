# -*- coding: utf-8 -*-
###################################################################################
#
#    A2A Digtial 
#    Copyright (C) 2021-TODAY A2A Digital (<https://www.a2adigital.com>).
#
###################################################################################
{
    'name': 'Sport Management',
    'summary': """Sport Management with Online Booking System""",
    'version': '14.0.1.0.0',
    'author': 'Hong Tean (A2A Digital)',
    'website': "https://a2a-digital.com/",
    'company': 'A2A Digital',
    "category": "Industries",
    'depends': ['base','base_setup', 'account', 'mail', 'website'],
    'data': [
             'security/salon_security.xml',
             'security/ir.model.access.csv',
             'data/data_chair.xml',
             'data/data_booking.xml',
             'views/salon_holiday.xml',
             'views/js_view.xml',
             'views/salon_data.xml',
             'views/salon_management_chair.xml',
             'views/salon_management_services.xml',
             'views/salon_order_view.xml',
             'views/salon_management_dashboard.xml',
             'views/booking_backend.xml',
             'views/salon_email_template.xml',
             'views/salon_config.xml',
             'views/working_hours.xml',
             'views/salon_management_duration.xml',
             'wizard/salon_booking_email.xml',
             'wizard/salon_booking_payment.xml',
             'templates/salon_booking_templates.xml',
             ],
    'images': ['static/description/banner.jpg'],
    # Module Price
    'price':130.00,
    # Module Currency Price
    'currency':'USD',
    'license': 'OPL-1',
    'installable': True,
    'application': True,
    'auto_install': False,
}
