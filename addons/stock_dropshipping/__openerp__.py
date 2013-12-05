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
    'name': 'Dropshipping Module',
    'version': '1.0',
    'category': 'Hidden',
    'summary': 'Dropshipping',
    'description': """
Manage sales quotations and stock locations
==========================================

This adds the route to make dropshipping sales orders in which the product sold are directly transfered from the reseller to the customer (direct delivery) without creating any internal document for the transfer.

""",
    'author': 'OpenERP SA',
    'website': 'http://www.openerp.com',
    'images': [],
    'depends': ['purchase', 'sale_stock'],
    'init_xml': [],
    'data': ['stock_dropshipping.xml'],
    'demo_xml': [],
    'test': [
        'test/cancellation_propagated.yml',
        'test/crossdock.yml',
        'test/dropship.yml',
        'test/procurementexception.yml',
        'test/lifo_price.yml'
        ],
    'installable': True,
    'auto_install': True,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
