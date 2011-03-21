# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2009 (<http://www.filsystem.ro>). All Rights Reserved
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
    "name" : "Romania - Chart of Accounts",
    "version" : "1.1",
    "author" : "filsys",
    "website": "http://www.filsystem.ro",
    "category" : "Finance",
    "depends" : ["account_chart", 'base_vat'],
    "description": """
This is the module to manage the accounting chart, VAT structure and Registration Number for Romania in OpenERP.
================================================================================================================
    """,
    "demo_xml" : [],
    "update_xml" : ['partner_view.xml','account_tax_code.xml','account_chart.xml','account_tax.xml','l10n_chart_ro_wizard.xml'],
    "active": False,
    "installable": True,
    "certificate" : "001308250150602948125",
    'images': ['images/config_chart_l10n_ro.jpeg','images/l10n_ro_chart.jpeg'],
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

