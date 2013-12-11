##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#    Copyright (C) 2010-2011 OpenERP S.A. (<http://www.openerp.com>).
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
    "name" : "Product extension to track sales and purchases",
    "version" : "1.0",
    "author" : "OpenERP S.A.",
    "depends" : ["product", "purchase", "sale", "mrp", "stock_account"],
    "category" : "Generic Modules/Inventory Control",
    "description": """
Product extension. This module adds:
  * Last purchase order for each product supplier 
  * New functional field: Available stock (real+outgoing stock)
  * Computes standard price from the BoM of the product (optional for each product)
  * Standard price is shown in the BoM and it can be computed with a wizard 
""",
    "init_xml" : [],
    "demo_xml" : [],
    "data" : ["product_extended_wizard.xml","product_extended_view.xml","mrp_view.xml", 'security/ir.model.access.csv'],
    "active": False,
    "installable": True
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

