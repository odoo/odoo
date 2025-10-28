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
    'name': 'Open HRMS Employee Documents Expiry',
    'version': '19.0.1.0.0',
    'category': 'Human Resources',
    'summary': """Manages Employee Documents With Expiry Notifications.""",
    'description': """OH Addon: Manages Employee Related Documents with Expiry
     Notifications. As such dates approach, the system is programmed to send
     automated alerts to relevant employees.These timely notifications are
     essential for ensuring that necessary actions can be taken to update 
     or renew documents before they lapse, thereby avoiding potential legal,
     regulatory, or operational complications that may arise from expired 
     documentation.""",
    'live_test_url': 'https://youtu.be/4fe5tzAG8Ng',
    'author': 'Cybrosys Techno solutions,Open HRMS',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': "https://www.openhrms.com",
    'depends': ['hr'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'views/document_type_views.xml',
        'views/hr_document_views.xml',
        'views/hr_employee_document_views.xml',
    ],
    'demo': [
        'data/document_type_demo.xml',
        'data/hr_work_location_demo.xml',
        'data/hr_employee_demo.xml',
        'data/hr_employee_document_demo.xml',
    ],
    'images': ['static/description/banner.jpg'],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
