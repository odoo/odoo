# -*- encoding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) conexus
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
    "name" : "Austria - Accounting",
    "version" : "1.0",
    "author" : "conexus.at",
    "website" : "http://www.conexus.at",
    "category" : "Localization/Account Charts",
    "depends" : ["account_chart", 'base_vat'],
    "description": """
This module provides the standard Accounting Chart for Austria which is based on
the Template from BMF.gv.at. Please keep in mind that you should review and adapt
it with your Accountant, before using it in a live Environment.""",
    "demo_xml" : [],
    "update_xml" : ['account_tax_code.xml',"account_chart.xml",'account_tax.xml',"l10n_chart_at_wizard.xml"],
    "auto_install": False,
    "installable": True
}


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
