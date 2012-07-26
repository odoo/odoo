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
    'name': 'Create Tasks on SO',
    'version': '1.0',
    "category": "Project Management",
    'description': """
Automatically creates project tasks from procurement lines.
===========================================================

This module will automatically create a new task for each procurement order line
(e.g. for sale order lines), if the corresponding product meets the following
characteristics:

    * Product Type = Service
    * Procurement Method (Order fulfillment) = MTO (Make to Order)
    * Supply/Procurement Method = Manufacture

If on top of that a projet is specified on the product form (in the Procurement
tab), then the new task will be created in that specific project. Otherwise, the
new task will not belong to any project, and may be added to a project manually
later.

When the project task is completed or cancelled, the workflow of the corresponding
procurement line is updated accordingly. For example, if this procurement corresponds
to a sale order line, the sale order line will be considered delivered when the
task is completed.
""",
    'author': 'OpenERP SA',
    'website': 'http://www.openerp.com',
    'images': ['images/product.jpeg', 'images/task_from_SO.jpeg'],
    'depends': ['project', 'procurement', 'sale', 'mrp_jit'],
    'init_xml': [],
    'update_xml': ['project_mrp_workflow.xml', 'process/project_mrp_process.xml', 'project_mrp_view.xml'],
    'demo_xml': ['project_mrp_demo.xml'],
    'test': ['test/project_task_procurement.yml'],
    'installable': True,
    'auto_install': False,
    'certificate': '0031976495453',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
