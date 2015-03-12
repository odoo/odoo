# -*- coding: utf-8 -*-
##############################################################################
#
#   Copyright (C) 2013-2014 7Gates Interactive Technologies 
#                           <http://www.7gates.co>
#                 @author Erdem Uney
#   
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as
#   published by the Free Software Foundation, either version 3 of the
#   License, or (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{
    'name': 'Turkish - Accounting',
    'version': '0.7',
    'license': 'AGPL-3',
    'category': 'Localization/Account Charts',
    'description': """
Base module for the Turkish localization
========================================

This module consists of:
    - Generic Turkish Chart of Accounts 
    - Turkish Taxes
    - Tax and legal related fields

For future development this will be a base for the Turkish localization.

*** Please keep in mind that you should review and adapt it with your Accountant, before using it in a live environment.
    """,
    'author': '7Gates Interactive Technologies',
    'maintainer': 'http://www.7gates.co',
    'website': 'http://www.odooturkiye.org',
    'depends': [
        'account',
        'base_vat',
        'account_chart',
        'base_iban',
    ],
    'data': [
        # 'data/account_type_template.xml',
        'data/account_uniform_chart_template.xml',
        'data/account_tax_code_template.xml',
        'data/account_chart_template.xml',
        'data/account_tax_template.xml',
        'view/l10n_tr_wizard.xml',
        'view/res_partner_view.xml',
        'view/res_company_view.xml',
    ],
    'installable': True,
}
