# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2009 Grzegorz Grzelak grzegorz.grzelak@cirrus.pl
#    All Rights Reserved
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
    "name" : "Poland - Chart of Accounts",
    "version" : "1.0",
    "author" : "Grzegorz Grzelak (Cirrus)",
    "website": "http://www.cirrus.pl",
    "category" : "Finance",
    "description": """
     This is the module to manage the accounting chart and taxes for Poland in OpenERP.
     ==================================================================================

     To jest moduł do tworzenia wzorcowego planu kont i podstawowych ustawień do podatków
     VAT 0%, 7% i 22%. Moduł ustawia też konta do kupna i sprzedaży towarów zakładając,
     że wszystkie towary są w obrocie hurtowym.
    """,
    "depends" : ["account", "base_iban", "base_vat", "account_chart"],
    "demo_xml" : [],
    "update_xml" : ['account_tax_code.xml',"account_chart.xml",
                    'account_tax.xml','l10n_chart_pl_wizard.xml'],
    "active": False,
    "installable": True,
    "certificate" : "00885794372803776829",
    'images': ['images/config_chart_l10n_pl.jpeg','images/l10n_pl_chart.jpeg'],
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

