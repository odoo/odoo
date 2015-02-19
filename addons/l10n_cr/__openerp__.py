# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo Business Applications
#    Addons modules by ClearCorp S.A.
#    Copyright (C) 2009-TODAY ClearCorp S.A. (<http://clearcorp.co.cr>).
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
    'name': 'Costa Rica - Accounting',
    'version': '1.0',
    'url': 'https://github.com/OCA/l10n-costa-rica',
    'author': 'ClearCorp',
    'website': 'http://clearcorp.cr',
    'category': 'Localization/Account Charts',
    'description': """
Chart of accounts for Costa Rica.
=================================

Includes:
---------
    * Account types: based on default ones.
    * Account chart template: 1 generic chart of accounts for now, more to come.
    * Tax templates: including 13% IV, 10% IV, 10% IS and ISC.
    * Tax codes templates: ready for the D-104 tax declaration.
    * An example of fiscal position.

Everything is in English with Spanish translation. Further translations are welcome,
please go to https://github.com/OCA/l10n-costa-rica.
    """,
    'depends': ['account', 'account_chart', 'base'],
    'demo': [],
    'data': [
        'l10n_cr_base_data.xml',
        'data/account_account_type.xml',
        'data/account_account_template.xml',
        'data/account_tax_code_template.xml',
        'data/account_chart_template.xml',
        'data/account_tax_template.xml',
        'data/account_fiscal_position_template.xml',
        'l10n_wizard.xml',
    ],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
