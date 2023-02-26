# -*- coding: utf-8 -*-
###################################################################################
#    A part of Open HRMS Project <https://www.openhrms.com>
#
#    Cybrosys Technologies Pvt. Ltd.
#    Copyright (C) 2022-TODAY Cybrosys Technologies (<https://www.cybrosys.com>).
#    Author: Aswani PC (<https://www.cybrosys.com>)
#
#    This program is free software: you can modify
#    it under the terms of the GNU Affero General Public License (AGPL) as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
###################################################################################
{
    'name': "Open HRMS - HR Dashboard",
    'version': '16.0.1.0.1',
    'summary': """Open HRMS - HR Dashboard""",
    'description': """Open HRMS - HR Dashboard""",
    'category': 'Generic Modules/Human Resources',
    'live_test_url': 'https://youtu.be/XwGGvZbv6sc',
    'author': 'Cybrosys Techno solutions,Open HRMS',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': "https://www.openhrms.com",
    'depends': ['hr', 'hr_holidays', 'hr_timesheet', 'hr_payroll_community',
                'hr_attendance', 'hr_timesheet_attendance',
                'hr_recruitment', 'hr_resignation', 'event',
                'hr_reward_warning', 'base'],
    'external_dependencies': {
        'python': ['pandas'],
    },
    'data': [
        'security/ir.model.access.csv',
        'report/broadfactor.xml',
        'views/dashboard_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'hrms_dashboard/static/src/css/hrms_dashboard.css',
            'hrms_dashboard/static/src/css/lib/nv.d3.css',
            'hrms_dashboard/static/src/js/hrms_dashboard.js',
            'hrms_dashboard/static/src/js/lib/d3.min.js',
            'hrms_dashboard/static/src/xml/hrms_dashboard.xml',
        ],
    },

    'images': ["static/description/banner.png"],
    'license': "AGPL-3",
    'installable': True,
    'application': True,
}
