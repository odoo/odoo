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
    'name': 'Open HRMS Employee History',
    'version': '19.0.1.0.0',
    'category': 'Human Resources',
    'summary': """Various Histories related to an employee. """,
    'description': """This module tracks the Job/Department History, Salary History, 
     Contract History and Hourly Cost History of the employees in a company""",
    'live_test_url': 'https://youtu.be/TaaDrBn3csc',
    'author': 'Cybrosys Techno solutions,Open HRMS',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': "https://www.openhrms.com, https://cybrosys.com",
    'depends': ['hr', 'oh_employee_creation_from_user',
                'hr_hourly_cost'],
    'data': [
        'security/ir.model.access.csv',
        'views/contract_history_views.xml',
        'views/department_history_views.xml',
        'views/hr_employee_views.xml',
        'views/salary_history_views.xml',
        'views/hourly_cost_views.xml',
    ],
    'images': ['static/description/banner.jpg'],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}

