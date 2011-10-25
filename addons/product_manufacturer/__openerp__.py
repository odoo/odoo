##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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
    "name" : "Products Attributes & Manufacturers",
    "version" : "1.0",
    "author" : "OpenERP SA",
    "category" : "Hidden",
    'complexity': "easy",
    "depends" : ["stock"],
    "init_xml" : [],
    "demo_xml" : [],
    "description": """
A module that adds manufacturers and attributes on the product form.
====================================================================

You can now define the following for a product:
    * Manufacturer
    * Manufacturer Product Name
    * Manufacturer Product Code
    * Product Attributes
    """,
    "update_xml" : [
        "security/ir.model.access.csv",
        "product_manufacturer_view.xml"
    ],
    "active": False,
    "installable": True,
    "certificate" : "00720153953662760781",
    'images': ['images/products_manufacturer.jpeg'],
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
