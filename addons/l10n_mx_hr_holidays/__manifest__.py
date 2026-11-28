# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Mexico - Time Off',
    'countries': ['mx'],
    'category': 'Human Resources/Time Off',
    'summary': 'Statutory vacations of the Mexican Federal Labor Law',
    'description': """
Mexican Time Off
================

    * Statutory vacations accrual plan (LFT, art. 76)
    * Accrual allocations start on the first contract date by default
    """,
    'depends': ['hr_holidays'],
    'auto_install': ['hr_holidays'],
    'data': [
        'data/hr_leave_accrual_plan_data.xml',
    ],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
