# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Anusha C (odoo@cybrosys.com)
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
    'name': "Sticky Header And Column In List View",
    'version': '16.0.1.0.0',
    'category': 'Extra Tools',
    'summary': """Enhance list views with sticky headers and columns for 
    improved navigation and readability.""",
    'description': """This module enhances Odoo list views by introducing sticky
     headers and columns. When scrolling through long lists, the header and 
     selected columns remain visible, providing context and easy access to 
     column information. Users can interact with data more effectively without 
     losing track of column titles.""",
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': "https://www.cybrosys.com",
    'depends': ['account', 'purchase', 'hr_expense', 'web'],
    'assets': {
        'web.assets_backend': [
            'list_view_sticky_header_and_column/static/src/js/'
            'list_view_sticky_header_and_column.js',
            'list_view_sticky_header_and_column/static/src/xml/'
            'list_view_sticky_header_and_column.xml',
            "list_view_sticky_header_and_column/static/src/scss/"
            "list_view_sticky_header_and_column.scss"
        ],
    },
    'images': ['static/description/banner.jpg'],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
