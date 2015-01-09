# -*- encoding: utf-8 -*-
##############################################################################
#
#    @author -  Fekete Mihai <feketemihai@gmail.com>
#    Copyright (C) 2011 TOTAL PC SYSTEMS (http://www.www.erpsystems.ro). 
#    Copyright (C) 2009 (<http://www.filsystem.ro>)
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
    "author" : "ERPsystems Solutions",
    "website": "http://www.erpsystems.ro",
    "category" : "Localization/Account Charts",
    "depends" : ['account','account_chart','base_vat'],
    "description": """
This is the module to manage the Accounting Chart, VAT structure, Fiscal Position and Tax Mapping.
It also adds the Registration Number for Romania in OpenERP.
================================================================================================================

Romanian accounting chart and localization.
    """,
    "demo" : [],
    "data" : ['partner_view.xml',
              'account_chart.xml',
              'account_tax_code_template.xml',
              'account_chart_template.xml',
              'account_tax_template.xml',
              'fiscal_position_template.xml',
              'l10n_chart_ro_wizard.xml',
              ],
    "installable": True,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

