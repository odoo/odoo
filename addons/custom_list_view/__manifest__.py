# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
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
    'name': 'Custom List View',
    'version': '16.0.1.2.0',
    'category': 'Extra Tools',
    'summary': 'Helps to Show Row Number, Fixed Header, Duplicate Record, '
               'Highlight Selected Record, Print and Copy Listview items',
    'description': "This module Helps to Show Row Number, Fixed Header, "
                   "Duplicate Record and Highlight Selected Record in List "
                   "View. Using this module the list view items can be printed"
                   " in pdf, excel and csv format, Also there is copy to "
                   "clipboard and pagination features.",
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': 'https://www.cybrosys.com',
    'depends': ['web', 'account'],
    'data': [
        'report/custom_list_view_templates.xml',
        'report/custom_list_view_reports.xml'
    ],
    'assets': {
        'web.assets_backend': [
            'custom_list_view/static/src/**/*',
        ]
    },
    'images': ['static/description/banner.png'],
    'licence': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False
}
