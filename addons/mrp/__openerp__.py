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
    "name" : "MRP",
    "version" : "1.1",
    "author" : "OpenERP SA",
    "website" : "http://www.openerp.com",
    "category" : "Manufacturing",
    "sequence": 18,
    "images" : ["images/bill_of_materials.jpeg", "images/manufacturing_order.jpeg", "images/planning_manufacturing_order.jpeg", "images/production_analysis.jpeg", "images/production_dashboard.jpeg","images/routings.jpeg","images/work_centers.jpeg"],
    "depends" : ["procurement", "stock", "resource", "purchase", "product","process"],
    "description": """
This is the base module to manage the manufacturing process in OpenERP.
=======================================================================

Features:
---------
    * Make to Stock / Make to Order (by line)
    * Multi-level BoMs, no limit
    * Multi-level routing, no limit
    * Routing and work center integrated with analytic accounting
    * Scheduler computation periodically / Just In Time module
    * Multi-pos, multi-warehouse
    * Different reordering policies
    * Cost method by product: standard price, average price
    * Easy analysis of troubles or needs
    * Very flexible
    * Allows to browse Bill of Materials in complete structure that include child and phantom BoMs

It supports complete integration and planification of stockable goods,
consumable of services. Services are completely integrated with the rest
of the software. For instance, you can set up a sub-contracting service
in a BoM to automatically purchase on order the assembly of your production.

Reports provided by this module:
--------------------------------
    * Bill of Material structure and components
    * Load forecast on Work Centers
    * Print a production order
    * Stock forecasts

Dashboard provided by this module:
----------------------------------
    * List of next production orders
    * List of procurements in exception
    * Graph of work center load
    * Graph of stock value variation
    """,
    'init_xml': [],
    'update_xml': [
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
    'demo_xml': [
         'mrp_demo.xml',
    ],
    'test': [
         'test/order_demo.yml',
         'test/order_process.yml',
         'test/cancel_order.yml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'certificate': '0032052481373',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
