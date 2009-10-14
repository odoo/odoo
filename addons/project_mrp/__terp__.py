# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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
    'name': 'Project Management - MRP and Sale Integration',
    'version': '1.0',
    'category': 'Generic Modules/Projects & Services',
    'description': """
This module is used to automatically create tasks based on different
procurements: sales order, manufacturing order, ...

It is mainly used to invoices services based on tasks automatically
created by sales orders.
""",
    'author': 'Tiny',
    'website': 'http://www.openerp.com',
    'depends': ['project', 'mrp', 'sale', 'mrp_jit'],
    'init_xml': [],
    'update_xml': ['project_workflow.xml', 'process/project_mrp_process.xml'],
    'demo_xml': [],
    'installable': True,
    'active': False,
    'certificate': '0031976495453',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
