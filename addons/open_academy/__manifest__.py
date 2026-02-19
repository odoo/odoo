# -*- coding: utf-8 -*-
###############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Dhanya Babu (<https://www.cybrosys.com>)
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
###############################################################################
{
    'name': "Odoo 16 Development Tutorials",
    'version': '16.0.1.0.0',
    'summary': """
        This module containing Odoo13, Odoo14, odoo15, odoo16 Tutorials, and 
        also how to configure pycharm in ubuntu""",
    'description': """
           This module containing Odoo13, Odoo14, odoo15, odoo16 Tutorials """,
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': 'https://www.cybrosys.com',
    'category': 'Website/eLearning',
    'depends': ['base', 'board', 'website_slides'],
    'data': [
        'data/slide_channel_data_v14.xml',
        'data/slide_channel_data_v13.xml',
        'data/slide_channel_data_v15.xml',
        'data/slide_channel_data_v16.xml',
        'security/openacademy_groups.xml',
        'security/openacademy_security.xml',
        'security/ir.model.access.csv',
        'wizard/openacademy_wizard_views.xml',
        'views/res_partner_views.xml',
        'views/open_academy_session_views.xml',
        'views/open_academy_course_views.xml',
        'views/board_views.xml',
        'report/openacademy_session_reports.xml',
    ],
    'images': ['static/description/banner.png'],
    'license': 'AGPL-3',
    'installable': True,
    'application': True,
    'auto_install': False,
    'demo': [
        'demo/openacademy_demo.xml',
    ],
}
