# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2008 P. Christeas. All Rights Reserved
#
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    "name" : "Greek Fiscal printing",
    "version" : "0.1",
    "depends" : ["account" ],
    "author" : "P. Christeas",
    "description": """This enables the greek fiscal printing of reports (invoices). 
    When an invoice is settled, it is marked by the (legal) fiscal machine and locked
    down. Then, it is printed according to the law.
    """,
    "website" : "http://www.hellug.gr",
    "category" : "Generic Modules/Accounting",
    "init_xml" : [ "account_invoice_data.xml",
    ],
    "demo_xml" : [
    ],
    "update_xml" : [ "account_fiscalgr_vats.xml",
	"account_fiscalgr_view.xml", 
	"account_invoice_report.xml",
	"security/ir.model.access.csv",
	"doytable.xml"
	],
    "active": False,
    "installable": True
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

