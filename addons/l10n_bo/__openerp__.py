# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2012 Cubic ERP - Teradata SAC (<http://cubicerp.com>).
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
    "name": "Bolivia Localization Chart Account",
    "version": "1.0",
    "description": """
Bolivian accounting chart and tax localization.

Plan contable boliviano e impuestos de acuerdo a disposiciones vigentes

    """,
    "author": "Cubic ERP",
    "website": "http://cubicERP.com",
    "category": "Localization/Account Charts",
    "depends": [
			"account_chart",
			],
	"data":[
        "account_tax_code.xml",
        "l10n_bo_chart.xml",
        "account_tax.xml",
        "l10n_bo_wizard.xml",			
			],
    "demo_xml": [
			],
    "data": [
			],
    "active": False,
    "installable": True,
    "certificate" : "",

}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
