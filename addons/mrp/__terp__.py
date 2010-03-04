# -*- encoding: utf-8 -*-
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
    "name" : "Manufacturing Resource Planning",
    "version" : "1.1",
    "author" : "Tiny",
    "website" : "http://www.openerp.com",
    "category" : "Generic Modules/Production",
    "depends" : ["stock", "hr", "purchase", "product","process"],
    "description": """
    This is the base module to manage the manufacturing process in Open ERP.

    Features:
    * Make to Stock / Make to Order (by line)
    * Multi-level BoMs, no limit
    * Multi-level routing, no limit
    * Routing and workcenter integrated with analytic accounting
    * Scheduler computation periodically / Just In Time module
    * Multi-pos, multi-warehouse
    * Different reordering policies
    * Cost method by product: standard price, average price
    * Easy analysis of troubles or needs
    * Very flexible
    * Allows to browse Bill of Materials in complete structure
        that include child and phantom BoMs
    It supports complete integration and planification of stockable goods,
    consumable of services. Services are completely integrated with the rest
    of the software. For instance, you can set up a sub-contracting service
    in a BoM to automatically purchase on order the assembly of your production.

    Reports provided by this module:
    * Bill of Material structure and components
    * Load forecast on workcenters
    * Print a production order
    * Stock forecasts
    """,
    'author': 'Tiny',
    'website': 'http://www.openerp.com',
    'depends': ['stock', 'hr', 'purchase', 'product', 'process'],
    'init_xml': [],
    'update_xml': [
        'security/mrp_security.xml',
        'security/ir.model.access.csv',
        'mrp_workflow.xml',
        'mrp_data.xml',
        'mrp_view.xml',
        'mrp_wizard.xml',
        'mrp_report.xml',
        'company_view.xml',
        'process/stockable_product_process.xml',
        'process/service_product_process.xml',
        'process/procurement_process.xml'
    ],
    'demo_xml': ['mrp_demo.xml', 'mrp_order_point.xml', 'mrp_test.xml'],
    'installable': True,
    'active': False,
    'certificate': '0032052481373',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
