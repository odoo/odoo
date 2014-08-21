# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    This module is Copyright (c) 2014 QQBee (http://qqbee.com.vn).
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
    "name" : "Vietnam QĐ15 - Chart of Accounts",
    "version" : "1.0",
    "author" : "QQBee",
    'website': 'http://qqbee.com.vn',
    "category" : "Localization/Account Charts",
    "description": """
This is the module to manage the accounting chart for Vietnam in OpenERP.
========================================================================

This module applies to companies based in Vietnamese Accounting Standard (VAS).
Chế độ kế toán doanh nghiệp (QĐ 15/2006/QĐ-BTC)

**Credits:** General Solutions, QQBee.
""",
    "depends" : ["account","base_vat","base_iban"],
    "data" : [
        "account_tax_code.xml",
        "account_chart.xml",
        "account_tax.xml",
        "l10n_vn_wizard.xml"
	],
    "demo" : [],
    'auto_install': False,
    "installable": True,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
