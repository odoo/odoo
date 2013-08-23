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
    'name': 'MRP',
    'version': '1.1',
    'author': 'OpenERP SA',
    'website': 'http://www.openerp.com',
    'category': 'Manufacturing',
    'sequence': 18,
    'summary': 'Manufacturing Orders, Bill of Materials, Routing',
    'images': ['images/bill_of_materials.jpeg', 'images/manufacturing_order.jpeg', 'images/planning_manufacturing_order.jpeg', 'images/manufacturing_analysis.jpeg', 'images/production_dashboard.jpeg','images/routings.jpeg','images/work_centers.jpeg'],
    'depends': ['product','procurement', 'stock', 'resource', 'purchase','process'],
    'description': """
Manage the Manufacturing process in OpenERP
===========================================

The manufacturing module allows you to cover planning, ordering, stocks and the manufacturing or assembly of products from raw materials and components. It handles the consumption and production of products according to a bill of materials and the necessary operations on machinery, tools or human resources according to routings.

It supports complete integration and planification of stockable goods, consumables or services. Services are completely integrated with the rest of the software. For instance, you can set up a sub-contracting service in a bill of materials to automatically purchase on order the assembly of your production.

Key Features
------------
* Make to Stock/Make to Order
* Multi-level bill of materials, no limit
* Multi-level routing, no limit
* Routing and work center integrated with analytic accounting
* Periodical scheduler computation 
* Allows to browse bills of materials in a complete structure that includes child and phantom bills of materials

Dashboard / Reports for MRP will include:
-----------------------------------------
* Procurements in Exception (Graph)
* Stock Value Variation (Graph)
* Work Order Analysis
    """,
    'data': [
        'security/mrp_security.xml',
        'security/ir.model.access.csv',
        'mrp_workflow.xml',
        'mrp_data.xml',
        'wizard/mrp_product_produce_view.xml',
        'wizard/change_production_qty_view.xml',
        'wizard/mrp_price_view.xml',
        'wizard/mrp_workcenter_load_view.xml',
        'mrp_view.xml',
        'mrp_report.xml',
        'company_view.xml',
        'process/stockable_product_process.xml',
        'process/service_product_process.xml',
        'process/procurement_process.xml',
        'report/mrp_report_view.xml',
        'report/mrp_production_order_view.xml',
        'board_manufacturing_view.xml',
        'res_config_view.xml',
    ],
    'demo': ['mrp_demo.xml'],
    #TODO: This yml tests are needed to be completely reviewed again because the product wood panel is removed in product demo as it does not suit for new demo context of computer and consultant company
    # so the ymls are too complex to change at this stage
    'test': [
        'test/multicompany.yml',
#         'test/order_demo.yml',
#         'test/order_process.yml',
#         'test/cancel_order.yml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
