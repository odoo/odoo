# -*- coding: utf-8 -*-
{
    'name': 'HR Attendance - ZKTeco Device Integration',
    'version': '19.0.2.0.0',
    'category': 'Human Resources/Attendances',
    'summary': 'Receive attendance punches from ZKTeco face/fingerprint terminals (ADMS / iClock push protocol)',
    'description': """
HR Attendance - ZKTeco Device Integration
=========================================
Receives employee attendance punches pushed by ZKTeco biometric / face
recognition terminals using the ADMS / iClock push protocol.

* Device registry (serial number, communication key, location)
* Raw punch log storage with full audit trail
* Employee matching by Badge ID (hr.employee.barcode) or PIN
* Automatic check-in / check-out pairing into hr.attendance
* Real-time processing on push, plus a scheduled safety-net cron

Setup on the device (Menu > Comm > Cloud Server / ADMS):
  Server Address : <Odoo host / IP>
  Server Port    : <Odoo http_port, e.g. 8070>
  Enable Domain Name / ADMS : On

The device then calls /iclock/cdata, /iclock/getrequest and /iclock/ping.
    """,
    'author': 'OD19',
    'license': 'LGPL-3',
    'depends': [
        'hr',
        'hr_attendance',
        'hr_holidays',
        'od19_dashboard',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron.xml',
        'views/hr_attendance_device_views.xml',
        'views/hr_attendance_device_log_views.xml',
        'views/res_config_settings_views.xml',
        'views/menu.xml',
        'data/hr_attendance_dashboard_data.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    "icon": "/od19_hr_attendance_zkteco/static/description/icon.svg",
}
