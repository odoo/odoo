# -*- encoding: utf-8 -*-
###########################################################################
#    Module Writen for OpenERP, Open Source Management Solution
#    All Rights Reserved
###############Credits######################################################
#    Coded by: Alejandro Negrin anegrin@vauxoo.com,
#    Planified and Financed: Vauxoo
#    Audited by: Humberto Arocha (hbto@vauxoo.com)
#                Moises Lopez (moylop260@vauxoo.com)
#                Nhomar Hernández (nhomar@vauxoo.com)
#############################################################################
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
##############################################################################

{
    "name" : "Colombian - Accounting",
    "version" : "1.0",
    "author" : "Vauxoo",
    "category" : "Localization/Account Charts",
    "description": """
Chart of account for Colombia
=============================

Source of this chart of account is here_.

All the documentation available in this website is embeded in this module, to
be sure when you open OpenERP it has all necesary information to manage 
accounting en Colombia.

The law that enable this chart of account as valid for this country is 
available in this other link_.

This module has the intention to put available out of the box the chart of 
account for Colombia in Openerp.

We recommend install the module account_anglo_sxon to be able to have the cost
accounting correctly setted in out invoices.

.. _here: http://puc.com.co/
.. _link: http://puc.com.co/normatividad/
    """,
    "website" : "http://www.vauxoo.com/",
    "depends" : [
        "account",
        "base_vat",
        "base_iban",
        "account_chart",
    ],
    "demo" : [
    ],
    "data" : [
        "account_tax_code.xml",
        "account_chart.xml",
        "account_tax.xml",
        "l10n_chart_mx_wizard.xml"
    ],
    "active": False,
    "installable": True,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

