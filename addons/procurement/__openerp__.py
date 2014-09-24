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
    'website': 'https://www.odoo.com/page/manufacturing',
    'category' : 'Hidden/Dependency',
    'depends' : ['base', 'product'],
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
        'wizard/schedulers_all_view.xml',
        'procurement_view.xml',
        'company_view.xml',
    ],
    'demo': [],
    'test': ['test/procurement.yml'],
    'installable': True,
    'auto_install': True,
    'images': ['images/compute_schedulers.jpeg','images/config_companies_sched.jpeg', 'images/minimum_stock_rules.jpeg'],
}
