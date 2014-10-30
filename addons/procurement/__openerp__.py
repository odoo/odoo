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

This procurement module only depends on the product module and is not useful
on itself.  Procurements represent needs that need to be solved by a procurement
rule.  When a procurement is created, it is confirmed.  When a rule is found,
it will be put in running state.  After, it will check if what needed to be done
for the rule has been executed.  Then it will go to the done state.  A procurement
can also go into exception, for example when it can not find a rule and it can be cancelled.

The mechanism will be extended by several modules.  The procurement rule of stock will
create a move and the procurement will be fulfilled when the move is done.
The procurement rule of sale_service will create a task.  Those of purchase or
mrp will create a purchase order or a manufacturing order.

The scheduler will check if it can assign a rule to confirmed procurements and if
it can put running procurements to done.

Procurements in exception should be checked manually and can be re-run.
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
