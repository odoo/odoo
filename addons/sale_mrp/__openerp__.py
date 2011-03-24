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
    'name': 'Sales and MRP Management',
    'version': '1.0',
    'category': 'Sales',
    'description': """
This module provides facility to the user to install mrp and sales modulesat a time.
====================================================================================

It is basically used when we want to keep track of production
orders generated from sales order.
It adds sales name and sales Reference on production order.
    """,
    'author': 'OpenERP SA',
    'website': 'http://www.openerp.com',
    'images': ['images/SO_to_MO.jpeg'],
    'depends': ['mrp', 'sale'],
    'init_xml': [],
    'update_xml': [
        'security/sale_mrp_security.xml',
        'security/ir.model.access.csv',
        'sale_mrp_view.xml',
    ],
    'demo_xml': [],
    'test':['test/sale_mrp.yml'],
    'installable': True,
    'active': False,
    'certificate': '00395598976683092013',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
