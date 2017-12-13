# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright: (C) 2012 - TODAY Mentis d.o.o.
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
    "name": "Slovenian - Accounting",
    "version": "1.3",
    "author": "Mentis d.o.o.",
    "website": "http://www.mentis.si",
    "category": "Localization/Account Charts",
    "description": " ",
    "depends": ["account", "base_iban", "base_vat", "account_chart", "account_cancel"],
    "description": "Kontni načrt, davki in davčni obrazec za gospodarske družbe",
    "data": [
        "data/account.account.template.xml",
        "data/account.tax.code.template.xml",
        "data/account.chart.template.xml",
        "data/account.tax.template.xml",
        "data/account.fiscal.position.template.xml",
        "data/account.fiscal.position.account.template.xml",
        "data/account.fiscal.position.tax.template.xml",
        "data/res.bank.xml",
        "l10n_si_wizard.xml"
    ],
    'auto_install': False,
    "installable": True,
}
