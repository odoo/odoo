# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Afra MP (odoo@cybrosys.com)
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
    'name': 'Advanced Chatter View',
    'version': '16.0.1.0.0',
    'category': 'Productivity/Discuss',
    'summary': """Advanced odoo chatter view.""",
    'description': """This module is used to view advanced chatter.""",
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': "https://www.cybrosys.com",
    'depends': ['base', 'mail'],
    'assets': {
        'web.assets_backend': [
            "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.3/font/bootstrap-icons.css",
            'advanced_chatter_view/static/src/css/chatter_topbar.css',
            'advanced_chatter_view/static/src/js/chatter_container.js',
            'advanced_chatter_view/static/src/xml/chatter_topbar.xml',
            'advanced_chatter_view/static/src/xml/chatter.xml',
            'advanced_chatter_view/static/src/xml/chatter_container.xml'
        ],
    },
    'images': [
        'static/description/banner.png'],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
