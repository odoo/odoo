# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2008 Tiny SPRL (<http://tiny.be>). All Rights Reserved
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
    "name" : "Sales Management - Reporting",
    "version" : "1.0",
    "author" : "Tiny",
    "website" : "http://www.openerp.com",
    "depends" : ["sale"],
    "category" : "Generic Modules/Sales & Purchases",
    "description": """
    Reporting for the sale module:
    * Sales order by product (my/this month/all)
    * Sales order by category of product (my/this month/all)

    Some predefined lists:
    * Sales of the month
    * Open quotations
    * Uninvoiced Sales
    * Uninvoiced but shipped Sales
    """,
    "init_xml" : [],
    "demo_xml" : [],
    "update_xml" : [
        "security/ir.model.access.csv",
        "report_sale_view.xml",
        "report_sale_graph.xml",
    ],
    "active": False,
    "installable": True
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

