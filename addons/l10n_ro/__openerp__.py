# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2012 (<http://www.erpsystems.ro>). All Rights Reserved
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
    "name" : "Romania - Accounting",
    "version" : "1.0",
    "author" : "TOTAL PC SYSTEMS",
    "website": "http://www.erpsystems.ro",
    "category" : "Localization/Account Charts",
    "depends" : ['account','account_chart','base_vat'],
    "description": """
This is the module to manage the accounting chart, VAT structure and Registration Number for Romania in OpenERP.
================================================================================================================

Romanian accounting chart and localization.
    """,
    "demo_xml" : [],
    "update_xml" : ['partner_view.xml','account_tax_code_template.xml','account_chart.xml','account_tax_template.xml','l10n_chart_ro_wizard.xml'],
    "auto_install": False,
    "installable": True,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

