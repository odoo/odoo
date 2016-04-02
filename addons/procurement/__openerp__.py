# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name' : 'Procurements',
    'version' : '1.0',
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
        'product_product_view.xml',
    ],
    'demo': [],
    'test': ['test/procurement.yml'],
    'installable': True,
    'auto_install': True,
}
