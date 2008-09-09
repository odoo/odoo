# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2004-2008 Tiny SPRL (http://tiny.be) All Rights Reserved.
#
# $Id$
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
###############################################################################
{
    "name" : "Belgium - Plan Comptable Minimum Normalise",
    "version" : "1.1",
    "author" : "Tiny",
    "category" : "Localisation/Account charts",
    "depends" : ["account", "account_report", "base_vat", "base_iban",
        "account_chart"],
    "init_xml" : [],
    "description": """
    This is the base module to manage the accounting chart for Belgium in Tiny ERP.

    After Installing this module,The Configuration wizard for accounting is launched.
    * We have the account templates which can be helpful to generate Charts of Accounts.
    * On that particular wizard,You will be asked to pass the name of the company,the chart template to follow,the no. of digits to generate the code for your account and Bank account,currency  to create Journals.
        Thus,the pure copy of Chart Template is generated.
    * This is the same wizard that runs from Financial Managament/Configuration/Financial Accounting/Financial Accounts/Generate Chart of Accounts from a Chart Template.

    Wizards provided by this module:
    * Enlist the partners with their related VAT  and invoiced amounts.Prepares an XML file format.Path to access : Financial Management/Reporting/Listing of VAT Customers.
    * Prepares an XML file for Vat Declaration of the Main company of the User currently Logged in.Path to access : Financial Management/Reporting/Listing of VAT Customers.

    """,
    "demo_xml" : [
#        "account_demo.xml",
        "account.report.report.csv"
    ],
    "update_xml" : ["account_pcmn_belgium.xml","l10n_be_wizard.xml", "l10n_be_sequence.xml"],
    "installable": True
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

