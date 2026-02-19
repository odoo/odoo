# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Anfas Faisal K (<https://www.cybrosys.com>)
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
    'name': "Product Low Stock Alert",
    'version': '16.0.1.0.1',
    'summary': """Product Low Stock Alert Display in Point of Sale and 
    Product Views""",
    "category": 'Warehouse,Point of Sale',
    'description': """Module adds functionality to display product stock 
    alerts in the point of sale interface, indicating low stock levels for 
    products and also in the product template kanban and list view.""",
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': 'https://www.cybrosys.com',
    'depends': ['stock', 'point_of_sale'],
    'data': [
        'views/res_config_settings_views.xml',
        'views/product_product_views.xml',
        'views/product_template_views.xml'
    ],
    'assets': {
        'web.assets_backend': [
            'low_stocks_product_alert/static/src/css/template_color.css',
        ],
        'point_of_sale.assets': [
            'low_stocks_product_alert/static/src/xml/product_item_template.xml',
        ],
    },
    'images': ['static/description/banner.png'],
    'license': "LGPL-3",
    'installable': True,
    'application': False
}
