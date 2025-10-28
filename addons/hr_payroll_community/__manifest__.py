# -*- coding: utf-8 -*-
#############################################################################
#    A part of Open HRMS Project <https://www.openhrms.com>
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
{
    'name': 'Odoo 18 HR Payroll',
    'version': '19.0.1.0.0',
    'category': 'Human Resources',
    'summary': """Odoo 19 HR Payroll, Odoo19 Payroll, Payroll, Odoo Payroll,
    Payroll V19, Odoo19, Payroll Management, Odoo18 Payslip""",
    'description': """The system automates payroll management by streamlining
     key processes such as calculating employee salaries, deductions, and 
     benefits based on predefined rules and regulations. It also facilitates
     the automatic generation of detailed payslips, ensuring accuracy in 
     payment breakdowns for each employee. This reduces manual effort, 
     minimizes errors, and ensures compliance with tax and labor laws, while
     providing employees with timely and accurate payment information""",
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': 'https://www.openhrms.com',
    'depends': ['hr_holidays'],
    'data': [
        'data/ir_module_category_data.xml',
        'security/hr_payroll_community_security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/hr_payroll_community_data.xml',
        'wizard/hr_payslips_employees_views.xml',
        'wizard/payslip_lines_contribution_register_views.xml',
        'report/hr_payroll_report.xml',
        'report/report_contribution_register_templates.xml',
        'report/report_payslip_templates.xml',
        'report/report_payslip_details_templates.xml',
        'views/hr_leave_type_views.xml',
        'views/hr_version_views.xml',
        'views/hr_salary_rule_views.xml',
        'views/hr_salary_rule_category_views.xml',
        'views/hr_contribution_register_views.xml',
        'views/hr_payroll_structure_views.xml',
        'views/hr_payslip_views.xml',
        'views/hr_payslip_line_views.xml',
        'views/hr_employee_views.xml',
        'views/hr_payslip_run_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'demo': ['data/hr_payroll_community_demo.xml'],
    'images': ['static/description/banner.jpg'],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': True,
}
