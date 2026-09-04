# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions (<https://www.cybrosys.com>)
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
    'name': 'Easy Stock Movement',
    'version': '16.0.1.0.0',
    'category': 'Warehouse',
    'summary': 'This module is used transfer of stock from one location '
               'to another',
    'description': "Move stock from one location to another location with "
                   "easy interface",
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'images': ['static/description/banner.png'],
    'website': 'https://www.cybrosys.com',
    'depends': ['stock', 'product'],
    'data': [
        'security/ir.model.access.csv',
        'views/product_template_views.xml',
        'views/product_product_views.xml',
        'views/stock_picking_type_views.xml',
        'wizard/stock_transfer_views.xml'
    ],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
