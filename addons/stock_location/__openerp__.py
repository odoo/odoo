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
    'name': 'Advanced Routes',
    'version': '1.0',
    'category': 'Manufacturing',
    'description': """
This module supplements the Warehouse application by effectively implementing Push and Pull inventory flows.
============================================================================================================

Typically this could be used to:
--------------------------------
    * Manage product manufacturing chains
    * Manage default locations per product
    * Define routes within your warehouse according to business needs, such as:
        - Quality Control
        - After Sales Services
        - Supplier Returns

    * Help rental management, by generating automated return moves for rented products

Once this module is installed, an additional tab appear on the product form,
where you can add Push and Pull flow specifications. The demo data of CPU1
product for that push/pull :

Push flows:
-----------
Push flows are useful when the arrival of certain products in a given location
should always be followed by a corresponding move to another location, optionally
after a certain delay. The original Warehouse application already supports such
Push flow specifications on the Locations themselves, but these cannot be
refined per-product.

A push flow specification indicates which location is chained with which location,
and with what parameters. As soon as a given quantity of products is moved in the
source location, a chained move is automatically foreseen according to the
parameters set on the flow specification (destination location, delay, type of
move, journal). The new move can be automatically processed, or require a manual
confirmation, depending on the parameters.

Pull flows:
-----------
Pull flows are a bit different from Push flows, in the sense that they are not
related to the processing of product moves, but rather to the processing of
procurement orders. What is being pulled is a need, not directly products. A
classical example of Pull flow is when you have an Outlet company, with a parent
Company that is responsible for the supplies of the Outlet.

  [ Customer ] <- A - [ Outlet ]  <- B -  [ Holding ] <~ C ~ [ Supplier ]

When a new procurement order (A, coming from the confirmation of a Sale Order
for example) arrives in the Outlet, it is converted into another procurement
(B, via a Pull flow of type 'move') requested from the Holding. When procurement
order B is processed by the Holding company, and if the product is out of stock,
it can be converted into a Purchase Order (C) from the Supplier (Pull flow of
type Purchase). The result is that the procurement order, the need, is pushed
all the way between the Customer and Supplier.

Technically, Pull flows allow to process procurement orders differently, not
only depending on the product being considered, but also depending on which
location holds the "need" for that product (i.e. the destination location of
that procurement order).

Use-Case:
---------

You can use the demo data as follow:
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  **CPU1:** Sell some CPU1 from Chicago Shop and run the scheduler
     - Warehouse: delivery order, Chicago Shop: reception
  **CPU3:**
     - When receiving the product, it goes to Quality Control location then
       stored to shelf 2.
     - When delivering the customer: Pick List -> Packing -> Delivery Order from Gate A
    """,
    'author': 'OpenERP SA',
    'images': ['images/pulled_flow.jpeg','images/pushed_flow.jpeg'],
    'depends': ['procurement','stock','sale'],
    'init_xml': [],
    'update_xml': ['stock_location_view.xml', "security/stock_location_security.xml", 'security/ir.model.access.csv', 'procurement_pull_workflow.xml'],
    'demo_xml': [
        'stock_location_demo_cpu1.xml',
        'stock_location_demo_cpu3.yml',
    ],
    'installable': True,
    'test':[
            'test/stock_location_pull_flow.yml',
            'test/stock_location_push_flow.yml',
    ],
    'auto_install': False,
    'certificate': '0046505115101',
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
