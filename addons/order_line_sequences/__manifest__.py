# -*- coding: utf-8 -*-
################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Amaya Aravind (odoo@cybrosys.com)
#
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
################################################################################
{
    'name': 'Order Line Sequences/Line Numbers',
    'version': '16.0.1.0.0',
    'category': 'Extra Tools',
    'summary': 'Sequence numbers in order lines of sales,purchase and delivery.',
    'description': """This module will help you to add sequence for order lines
                      in sales, purchase and delivery. It will also add line 
                      numbers in report lines.""",
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': "https://www.cybrosys.com",
    'license': 'AGPL-3',
    'depends': ['base', 'sale_management', 'purchase', 'stock'],
    'data': [
        'views/sale_order_view.xml',
        'views/purchase_order_view.xml',
        'views/stock_view.xml',
        'views/sale_order_document_view.xml',
        'views/report_picking_view.xml',
        'views/report_purchaseorder_document_view.xml',
    ],
    'images': ['static/description/banner.png'],
    'installable': True,
    'auto_install': False,
    'application': False,
}
