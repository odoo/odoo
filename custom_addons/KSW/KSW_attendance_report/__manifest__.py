{
    'name': 'KSW Attendance Report',
    'version': '19.0.1.0.0',
    'category': 'Human Resources/Attendances',
    'summary': 'Monthly employee attendance PDF report',
    'depends': [
        'hr_attendance',
        'hr_biometric_attendance',
        'KSW_attendance_leave',
    ],
    'data': [
        'security/ir.model.access.csv',
        'report/attendance_report_template.xml',
        'views/attendance_report_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}

