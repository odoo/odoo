# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Employee Contracts Reporting',
    'version': '1.0',
    'category': 'Human Resources/Contracts',
    'description': """
Add a dynamic report about contracts and employees.
    """,
    'website': 'https://www.odoo.com/app/employees',
    'depends': ['hr_contract'],
    'data': [
        'security/ir.model.access.csv',
        'security/hr_contract_reports_security.xml',
        'report/hr_contract_employee_report_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'hr_contract_reports/static/src/js/hr_contract_employee_report_views.js',
        ],
        'web.qunit_suite_tests': [
            'hr_contract_reports/static/tests/*.js',
        ],
    },
    'installable': True,
    'auto_install': True,
    'license': 'OEEL-1',
}
