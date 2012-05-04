# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


{
    'name': 'Delivery Costs',
    'version': '1.0',
    'category': 'Sales Management',
    'complexity': "normal",
    'description': """
Allows you to add delivery methods in sale orders and picking.
==============================================================

You can define your own carrier and delivery grids for prices.
When creating invoices from picking, OpenERP is able to add and compute the shipping line.

     """,
    'author': 'OpenERP SA',
    'depends': ['sale', 'purchase', 'stock'],
    'init_xml': ['delivery_data.xml'],
    'update_xml': [
        'security/ir.model.access.csv',
        'wizard/delivery_sale_order_view.xml',
        'delivery_report.xml',
        'delivery_view.xml',
        'partner_view.xml',
        'res_config_view.xml'
    ],
    'demo_xml': ['delivery_demo.xml'],
    'test': [
        'test/delivery_cost.yml',
    ],
    'installable': True,
    'auto_install': False,
    'certificate': '0033981912253',
    'images': ['images/1_delivery_method.jpeg','images/2_delivery_pricelist.jpeg'],
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
