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
    'name': 'MRP Sub Product - To produce several products from one production order',
    'version': '1.0',
    'category': 'Generic Modules/Production',
    'description': """
This module allows you to produce several products from one production order.
=============================================================================

You can configure sub-products in the bill of material.

Without this module:
    A + B + C -> D

With this module:
    A + B + C -> D + E
    """,
    'author': 'OpenERP SA',
    'website': 'http://www.openerp.com',
    'images': ['images/bom_subproduct.jpeg'],
    'depends': ['base', 'mrp'],
    'init_xml': [],
    'update_xml': [
       'security/ir.model.access.csv',
       'mrp_subproduct_view.xml'
    ],
    'demo_xml': [],
    'test': ['test/mrp_subproduct.yml'],
    'installable': True,
    'active': False,
    'certificate': '0050060616733',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
