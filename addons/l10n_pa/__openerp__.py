# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2011 Cubic ERP - Teradata SAC (<http://cubicerp.com>).
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
    "name": "Panama Localization Chart Account",
    "version": "1.0",
    "description": """
Panamenian accounting chart and tax localization.

Plan contable panameño e impuestos de acuerdo a disposiciones vigentes

Con la Colaboración de 
- AHMNET CORP http://www.ahmnet.com

    """,
    "author": "Cubic ERP",
    "website": "http://cubicERP.com",
    "category": "Localization/Account Charts",
    "depends": [
			"account_chart",
			],
	"data":[
        "account_tax_code.xml",
        "l10n_pa_chart.xml",
        "account_tax.xml",
        "l10n_pa_wizard.xml",
			],
    "demo_xml": [
			],
    "active": False,
    "installable": True,
    "certificate" : "",
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
