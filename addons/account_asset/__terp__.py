# -*- encoding: utf-8 -*-
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
    "name" : "Asset management",
    "version" : "1.0",
    "depends" : ["account"],
    "author" : "Tiny",
    "description": """Financial and accounting asset management.
    Allows to define
    * Asset category. 
    * Assets.
    *Asset usage period and property.
    """,
    "website" : "http://www.openerp.com",
    "category" : "Generic Modules/Accounting",
    "init_xml" : [
    ],
    "demo_xml" : [
    ],
    "update_xml" : [
        "security/ir.model.access.csv",
        "account_asset_wizard.xml",
        "account_asset_view.xml",
        "account_asset_invoice_view.xml",
	"account_asset_report_view.xml",
	#modif
    ],
#   "translations" : {
#       "fr": "i18n/french_fr.csv"
#   },
    "active": False,
    "installable": True,

}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

