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
    'name': 'Stock No Auto-Picking',
    'version': '1.0',
    'category': 'Warehouse',
    'description': """
This module allows an intermediate picking process to provide raw materials to production orders.
=================================================================================================

One example of usage of this module is to manage production made by your
suppliers (sub-contracting). To achieve this, set the assembled product
which is sub-contracted to "No Auto-Picking" and put the location of the
supplier in the routing of the assembly operation.
    """,
    'author': 'OpenERP SA',
    'depends': ['mrp'],
    'images': ['images/auto_picking.jpeg'],
    'update_xml': ['stock_no_autopicking_view.xml'],
    'demo_xml': [],
    'test': ['test/stock_no_autopicking.yml'],
    'installable': True,
    'active': False,
    'certificate': '0075124168925',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
