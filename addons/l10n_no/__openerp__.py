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
    "name" : "Norway - Chart of Accounts",
    "version" : "1.0",
    "author" : "Rolv Råen",
    "category" : "Localization/Account Charts",
    "description": "This is the module to manage the accounting chart for Norway in Open ERP.",
    "depends" : ["account", "base_iban", "base_vat", "account_chart"],
    "demo_xml" : [],
    "data" : ['account_tax_code.xml',"account_chart.xml",
                    'account_tax.xml','l10n_chart_no_wizard.xml'],
    "active": False,
    "installable": True
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

