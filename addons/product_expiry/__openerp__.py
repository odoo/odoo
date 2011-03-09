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
    "name" : "Products date of expiry",
    "version" : "1.0",
    "author" : "OpenERP SA",
    "category" : "Warehouse",
    "depends" : ["stock"],
    "init_xml" : [],
    "demo_xml" : ["product_expiry_demo.xml"],
    "description": '''Track different dates on products and production lots:
 - end of life
 - best before date
 - removal date
 - alert date
Used, for example, in food industries.''',
    "update_xml" : ["product_expiry_view.xml"],
    "active": False,
    "installable": True,
    "certificate": "00421222123914960109",
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

