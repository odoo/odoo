# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Attendance Contracts',
    'version': '1.0',
    'category': 'Hidden',
    'summary': 'Consider employee contracts in attendance calculations',
    'description': """
This module aims to consider employee contracts for attendance calculations.
============================================================================

Uses contracts to calculate overtime.
       """,
    'depends': ['hr_attendance', 'hr_contract'],
    'installable': True,
    'auto_install': True,
    'license': 'LGPL-3',
}
