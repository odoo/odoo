# -*- coding: utf-8 -*-
#    Author: Leonardo Pistone
#    Copyright 2015 Camptocamp SA
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
{'name': 'Stock Dropshipping Dual Invoice',
 'summary':
 'Create both Supplier and Customer Invoices from a Dropshipping Delivery',
 'version': '0.1',
 'author': "Camptocamp,Odoo Community Association (OCA)",
 'category': 'Warehouse',
 'license': 'AGPL-3',
 'depends': ['stock_account',
             'sale_stock',
             'stock_dropshipping'],
 'data': [
     'wizard/stock_invoice_onshipping_view.xml',
     'security/group.xml',
 ],
 'auto_install': False,
 'installable': True,
 }
