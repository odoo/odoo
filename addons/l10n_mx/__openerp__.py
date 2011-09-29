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
    "name" : "Mexico - Chart of Account",
    "version" : "1.0",
    "author" : "RelTek Mexico",
    "category" : "Localization/Account Charts",
    "description": """
This is the module to manage the accounting chart for Mexico in OpenERP.
========================================================================

Mexican accounting chart and localization.
    """,
    "depends" : ["account", "base_vat", "account_chart"],
    "demo_xml" : [],
    "update_xml" : ['account_tax_code.xml',"account_chart.xml",
                    'account_tax.xml','l10n_chart_mx_wizard.xml'],
    "active": False,
    "installable": True,
    "certificate" : "00858539161332598061",
    'images': ['images/config_chart_l10n_mx.jpeg','images/l10n_mx_chart.jpeg'],
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

