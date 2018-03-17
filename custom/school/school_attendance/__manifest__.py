
{
    'name': 'School Attendances',
    'version': '1.0',
    'category': 'Education',
    'sequence': 81,
    'summary': 'Manage Students attendances',
    'description': """
This module aims to manage students attendances.
==================================================

Keeps account of the attendances of the students on the basis of the
actions(Check in/Check out) performed by them.
       """,
    'author': '''Francis Bangura. <francisbnagura@gmail.com>''',
    'website': 'https://www.byteltd.com/',
    'depends': ['school_settings', 'school', 'barcodes'],
    'data': [
        'security/school_attendance_security.xml',
        'security/ir.model.access.csv',
        'views/web_asset_backend_template.xml',
        'views/school_attendance_view.xml',
        'views/school_student_view.xml',
        'data/data.xml',
        'data/ir_config.xml',
        #'report/school_student_badge.xml',
        #'views/res_config_view.xml',
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'qweb': [
        "static/src/xml/attendance.xml",
    ],
    'application': True,
}
