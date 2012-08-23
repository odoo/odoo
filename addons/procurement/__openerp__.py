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
    'name' : 'Procurements',
    'version' : '1.0',
    'author' : 'OpenERP SA',
    'website' : 'http://www.openerp.com',
    'category' : 'Hidden/Dependency',
    'depends' : ['base','process', 'product', 'stock'],
    'description': """
This is the module for computing Procurements.
==============================================

In the MRP process, procurements orders are created to launch manufacturing
orders, purchase orders, stock allocations. Procurement orders are
generated automatically by the system and unless there is a problem, the
user will not be notified. In case of problems, the system will raise some
procurement exceptions to inform the user about blocking problems that need
to be resolved manually (like, missing BoM structure or missing supplier).

The procurement order will schedule a proposal for automatic procurement
for the product which needs replenishment. This procurement will start a
task, either a purchase order form for the supplier, or a production order
depending on the product's configuration.
    """,
    'data': [
        'security/ir.model.access.csv',
        'security/procurement_security.xml',
        'procurement_data.xml',
        'wizard/make_procurement_view.xml',
        'wizard/mrp_procurement_view.xml',
        'wizard/orderpoint_procurement_view.xml',
        'wizard/schedulers_all_view.xml',
        'procurement_view.xml',
        'procurement_workflow.xml',
        'process/procurement_process.xml',
        'company_view.xml',
        'board_mrp_procurement_view.xml',
    ],
    'demo': ['stock_orderpoint.xml'],
    'test': ['test/procurement.yml'],
    'installable': True,
    'auto_install': False,
    'certificate': '00954248826881074509',
    'images': ['images/compute_schedulers.jpeg','images/config_companies_sched.jpeg', 'images/minimum_stock_rules.jpeg'],
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
