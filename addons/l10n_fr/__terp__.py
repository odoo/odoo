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

#
# Plan comptable général pour la France, conforme au
# Règlement n° 99-03 du 29 avril 1999
# Version applicable au 1er janvier 2005.
# Règlement disponible sur http://comptabilite.erp-libre.info
# Mise en forme et paramétrage par http://sisalp.fr et http://nbconseil.net
#
{
    "name" : "France - Plan comptable Societe - 99-03",
    "version" : "1.1",
    "author" : "SISalp-NBconseil",
    "category" : "Localisation/Account Charts",
    "website": "http://erp-libre.info",
    "depends" : ["base", "account", "account_chart", 'base_vat'],
     "description": """
    This is the base module to manage the accounting chart for France in Open ERP.

    After Installing this module,The Configuration wizard for accounting is launched.
    * We have the account templates which can be helpful to generate Charts of Accounts.
    * On that particular wizard,You will be asked to pass the name of the company,the chart template to follow,the no. of digits to generate the code for your account and Bank account,currency  to create Journals.
        Thus,the pure copy of Chart Template is generated.
    * This is the same wizard that runs from Financial Management/Configuration/Financial Accounting/Financial Accounts/Generate Chart of Accounts from a Chart Template.

    * This module installs :
        The Tax Code chart and taxes for French Accounting.
    """,
    "init_xml" : ["fr_data.xml"],
    "update_xml" : ["l10n_fr_view.xml","types.xml", "plan-99-03_societe.xml",
                     "taxes.xml","fr_wizard.xml"],
    "demo_xml" : [],
    "installable": True
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

