# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
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
    'name': "One2many Search Widget",
    "version": "16.0.1.0.0",
    'summary': "Quick Search Feature For One2many Fields In Odoo",
    'description': 'One2Many Search Widget Helps the User to Search for a Word or Number. The One2many Rows Satisfying the '
               'Search will be Displayed and the Others get Hided.',
    "website": "https://www.cybrosys.com",
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'category': 'Extra Tools',
    "author": "Cybrosys Techno Solutions",
    "license": "AGPL-3",
    'depends': ['base', 'web'],
    'assets': {
        'web.assets_backend': [
            '/one2many_search_widget/static/src/css/header.css',
            '/one2many_search_widget/static/src/js/one2manySearch.js',
            '/one2many_search_widget/static/src/xml/one2manysearch.xml',
        ],
    },
    "installable": True,
    "application": False,
    'images': ['static/description/banner.png'],
    'auto_install': False,
}
