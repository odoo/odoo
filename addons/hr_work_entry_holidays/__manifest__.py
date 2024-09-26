# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Time Off - Work Entries',
    'version': '1.0',
    'category': 'Human Resources/Time Off',
    'sequence': 95,
    'summary': 'Manage Work Entries in Time Off',
    'description': """
Manage Work Entries in Time Off
===============================

This application allows you to integrate work entries in time off.
    """,
    'depends': ['hr_holidays', 'hr_work_entry'],
    # 'hr_holidays_contract', 'hr_work_entry_contract'],
    'data': [
        'data/hr_payroll_holidays_data.xml',
        'views/hr_leave_views.xml',
        'views/hr_leave_type_views.xml',
    ],
    'demo': ['data/hr_payroll_holidays_demo.xml'],
    'installable': True,
    'auto_install': True,
    'post_init_hook': '_validate_existing_work_entry',
    'license': 'LGPL-3',
}
