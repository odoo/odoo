# -*- coding: utf-8 -*-
{
    "name": "Zkteco, eSSL, Cams Biometrics Integration Module with HR Attendance",
    "version": "1.0",
    "category": "Generic Modules/Human Resources",
    "sequence": 50,
    "summary": "Syncronize employee attendances with biometric devices",
    "depends": ["hr", "hr_attendance"],
    "description": """
The module is developed based on the Cams Biometric web API documented in
https://camsunit.com/application/biometric-web-api.html.

It receives the biometric attendance in real-time and integrates it with the
hr.attendance model.

It supports all the cams biometrics machines listed at
https://camsunit.com/product/home.html

It also supports:

- ZKTeco

- eSSL

- Identix

- BioMax

- and more biometric machines provided that are verified
at https://developer.camsunit.com/.

This module requires a valid API license as listed in
https://camsunit.com/application/biometric-web-api.html#api_cost.
    """,
    

    'author': "Cams Biometrics",
    'category': 'Generic Modules/Human Resources',
    'version': '1.0',
    'license': 'AGPL-3',
    'company': 'Cams Biometrics',
    'website': "https://www.camsunit.com",
    'depends': ['hr','hr_attendance'],
    'installable': True,
    'images':[
        'static/description/banner.png',
        ],
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/config.xml',
        'views/inherited_employee_view.xml',
    ]
}
