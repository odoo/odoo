# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2014 Tech Receptives (<http://techreceptives.com>).
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
    'name': 'Singapore - Accounting',
    'version': '1.0',
    'author': 'Tech Receptives',
    'website': 'http://www.techreceptives.com',
    'category': 'Localization/Account Charts',
    'description': """
Singapore accounting chart and localization.
=======================================================

After installing this module, the Configuration wizard for accounting is launched.
    * The Chart of Accounts consists of the list of all the general ledger accounts
      required to maintain the transactions of Singapore.
    * On that particular wizard, you will be asked to pass the name of the company,
      the chart template to follow, the no. of digits to generate, the code for your
      account and bank account, currency to create journals.

    * The Chart of Taxes would display the different types/groups of taxes such as
      Standard Rates, Zeroed, Exempted, MES and Out of Scope.
    * The tax codes are specified considering the Tax Group and for easy accessibility of
      submission of GST Tax Report.

    """,
    'depends': ['base', 'account', 'account_chart'],
    'demo': [ ],
    'data': [
             'l10n_sg_chart_tax_code.xml',
             'l10n_sg_chart.xml',
             'l10n_sg_chart_tax.xml',
             'l10n_sg_wizard.xml',
    ],
    'installable': True,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
