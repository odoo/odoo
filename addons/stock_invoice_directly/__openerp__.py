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
    'name': 'Invoice Picking Directly',
    'version': '1.0',
    'category': 'Generic Modules/Sales & Purchases',
    'description': """
Invoice Wizard for Delivery.
============================

When you send or deliver goods, this module automatically launch
the invoicing wizard if the delivery is to be invoiced.
    """,
    'author': 'OpenERP SA',
    'website': 'http://www.openerp.com',
    'images': ['images/create_invoice.jpeg'],
    'depends': ['delivery', 'stock'],
    'init_xml': [],
    'update_xml': [],
    'demo_xml': [],
    'test': ['test/stock_invoice_directly.yml'],
    'installable': True,
    'active': False,
    'certificate': '0081385081261',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
