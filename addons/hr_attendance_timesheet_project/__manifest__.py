# -*- coding: utf-8 -*-
{
    'name': 'Attendance Project Timesheet Integration',
    'version': '1.0',
    'category': 'Human Resources/Attendances',
    'sequence': 95,
    'summary': 'Link employee attendance with projects and automatic timesheet generation',
    'description': """
Attendance Project Timesheet Integration
=========================================

This module integrates employee attendance with project management and timesheets:

Features:
---------
* Automatic timesheet creation when checking in
* Link attendance records to projects
* Remember last project for each employee
* Change project during work day (creates multiple timesheet entries)
* Kiosk mode support with project selection
* Default project "0 - Koszty Stałe" for general overhead

Workflow:
---------
1. Employee checks in → Creates timesheet entry for last used project (or default)
2. Employee can change project → Closes current timesheet, opens new one
3. Employee checks out → Closes active timesheet
4. Next check in → Automatically uses last project from previous day
    """,
    'author': 'Sage ERP',
    'depends': [
        'hr_attendance',
        'hr_timesheet',
        'project',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/default_project_data.xml',
        'views/hr_attendance_views.xml',
        'views/hr_employee_views.xml',
        'wizard/attendance_change_project_wizard_views.xml',
    ],
    'assets': {
        'hr_attendance.assets_public_attendance': [
            # Use ('append', ...) to ensure these load AFTER hr_attendance's files
            ('append', 'hr_attendance_timesheet_project/static/src/components/kiosk_action_choice/kiosk_action_choice.js'),
            ('append', 'hr_attendance_timesheet_project/static/src/components/kiosk_action_choice/kiosk_action_choice.xml'),
            ('append', 'hr_attendance_timesheet_project/static/src/components/kiosk_action_choice/kiosk_action_choice.scss'),
            # Patch MUST load last - after all components including ours
            ('append', 'hr_attendance_timesheet_project/static/src/public_kiosk_patch/public_kiosk_app_patch.js'),
        ],
        'web.assets_backend': [
            # Make KioskActionChoice component available in backend (for Dashboard)
            'hr_attendance_timesheet_project/static/src/components/kiosk_action_choice/kiosk_action_choice.js',
            'hr_attendance_timesheet_project/static/src/components/kiosk_action_choice/kiosk_action_choice.xml',
            'hr_attendance_timesheet_project/static/src/components/kiosk_action_choice/kiosk_action_choice.scss',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
