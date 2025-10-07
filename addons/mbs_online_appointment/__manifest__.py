# -*- coding: utf-8 -*-

{
    'name': "Online Patient's Appointment System",
    'category': 'Patient Appointment',
    'version': '16.0.0.8',
    'summary': 'Patient Appointment online registration ',
    'author': 'Mordant Buisness Solutions',
    'website': 'https://www.mordantbs.com',
    'license': 'OPL-1',
    'depends': ["base", "website"],
    'data': [
        "security/ir.model.access.csv",
        'data/sequence.xml',
        "views/menu.xml",
        "views/dr_details_template.xml",
        "views/patient_details_template.xml",
        'views/res_config_settings_views.xml',
        "views/submition_template.xml",
        "views/appointment_success_template.xml",
        "views/patient_registration_view.xml",
    ],

    'assets': {

        'web.assets_frontend': [
            '/mbs_online_appointment/static/src/js/state_change.js',
        ],
    },

    'demo': [

    ],
    'qweb': [

    ],
    'images': ['static/description/cover_image.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
