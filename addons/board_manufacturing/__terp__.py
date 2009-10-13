# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


{
    'name': 'Board for manufacturing',
    'version': '1.0',
    'category': 'Board/Manufacturing',
    'description': """
    This module creates a dashboards for Manufaturing that includes:
    * List of next production orders
    * List of deliveries (out packing)
    * Graph of workcenter load
    * List of procurement in exception
    """,
    'author': 'Tiny',
    'depends': ['board', 'mrp', 'stock', 'report_mrp'],
    'update_xml': ['board_manufacturing_view.xml'],
    'demo_xml': ['board_manufacturing_demo.xml'],
    'installable': True,
    'active': False,
    'certificate': '0030407612797',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
