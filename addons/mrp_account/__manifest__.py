# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Accounting - MRP',
    'version': '1.0',
    'category': 'Manufacturing/Manufacturing',
    'summary': 'Analytic accounting in Manufacturing',
    'description': """
Analytic Accounting in MRP
==========================

* Cost structure report

Also, allows to compute the cost of the product based on its BoM, using the costs of its components and work center operations.
It adds a button on the product itself but also an action in the list view of the products.
If the automated inventory valuation is active, the necessary accounting entries will be created.

""",
    'website': 'https://www.odoo.com/app/manufacturing',
    'depends': ['mrp', 'stock_account'],
    "data": [
        'security/ir.model.access.csv',
        "views/product_views.xml",
        "views/mrp_production_views.xml",
        "views/analytic_account_views.xml",
        "views/account_move_views.xml",
        "views/mrp_workcenter_views.xml",
        "report/report_mrp_templates.xml",
        "wizard/mrp_wip_accounting.xml",
    ],
    'demo': [
        'data/mrp_account_demo.xml',
    ],
    'installable': True,
    'auto_install': True,
    'post_init_hook': '_configure_journals',
    'license': 'LGPL-3',
}
