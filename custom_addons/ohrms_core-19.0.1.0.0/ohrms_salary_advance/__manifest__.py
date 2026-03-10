# -*- coding: utf-8 -*-
#############################################################################
#    A part of Open HRMS Project <https://www.openhrms.com>
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
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
    'name': 'Open HRMS Advance Salary',
    'version': '19.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Advance Salary In Open HRMS.',
    'description': """THis module is a component of Open HRMS suit. It module 
     helps the user to manage salary advance requests from employees. You can 
     configure advance salary rules, set advance salary limit, minimum number 
     of days, and provide advance salary to employees.""",
    'live_test_url': 'https://youtu.be/5OfoXRZ3AAY',
    'author': "Cybrosys Techno Solutions",
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': "https://www.openhrms.com",
    'depends': ['hr_payroll_community', 'hr', 'account', 'ohrms_loan',],
    'data': [
        'security/ir.model.access.csv',
        'security/salary_advance_security.xml',
        'data/ir_sequence_data.xml',
        'data/hr_salary_rule_data.xml',
        'views/salary_advance_views.xml',
    ],
    'images': ['static/description/banner.jpg'],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
