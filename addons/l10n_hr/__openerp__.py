# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Module: l10n_hr
#    Author: Goran Kliska
#    mail:   goran.kliska(AT)slobodni-programi.hr
#    Copyright: Slobodni programi d.o.o., Zagreb
#    Contributions:
#              Tomislav Bošnjaković, Storm Computers d.o.o. :
#                 - account types
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
    "name": "Croatia - RRIF 2012 COA",
    "description": """
Croatian localisation.
======================

Author: Goran Kliska, Slobodni programi d.o.o., Zagreb
        http://www.slobodni-programi.hr

Contributions:
  Tomislav Bošnjaković, Storm Computers: tipovi konta
  Ivan Vađić, Slobodni programi: tipovi konta

Description:

Croatian Chart of Accounts (RRIF ver.2012)

RRIF-ov računski plan za poduzetnike za 2012.
Vrste konta
Kontni plan prema RRIF-u, dorađen u smislu kraćenja naziva i dodavanja analitika
Porezne grupe prema poreznoj prijavi
Porezi PDV obrasca
Ostali porezi 
Osnovne fiskalne pozicije

Izvori podataka:
 http://www.rrif.hr/dok/preuzimanje/rrif-rp2011.rar
 http://www.rrif.hr/dok/preuzimanje/rrif-rp2012.rar

""",
    "version": "12.2",
    "author": "OpenERP Croatian Community",
    "category": 'Localization/Account Charts',
    "website": "https://code.launchpad.net/openobject-croatia",

    'depends': [
                'account',
                'account_chart',
                ],
    'data': [
                'data/account.account.type.csv',
                'data/account.tax.code.template.csv',
                'data/account.account.template.csv',
                'l10n_hr_chart_template.xml',
                'l10n_hr_wizard.xml',
                'data/account.tax.template.csv',
                'data/fiscal_position_template.xml',
            ],
    "demo": [],
    'test': [],
    "active": False,
    "installable": True,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
