# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright 2013 Camptocamp SA
#    Copyright 2013 Akretion
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

{'name': 'Connector for E-Commerce',
 'version': '8.0.3.0.0',
 'category': 'Hidden',
 'author': "Camptocamp,Akretion,Odoo Community Association (OCA)",
 'website': 'http://openerp-connector.com',
 'license': 'AGPL-3',
 'depends': [
     'connector',
     'sale_payment_method_automatic_workflow',
     'sale_exceptions',
     'delivery',
     'connector_base_product',
 ],
 'data': [
     'security/security.xml',
     'security/ir.model.access.csv',
     'wizard/sale_ignore_cancel_view.xml',
     'sale_view.xml',
     'invoice_view.xml',
     'ecommerce_data.xml',
     'stock_view.xml',
     'payment_method_view.xml',
     'account_view.xml',
 ],
 'installable': False,
 }
