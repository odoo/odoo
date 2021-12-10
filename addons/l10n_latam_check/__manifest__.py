##############################################################################
#
#    Copyright (C) 2015  ADHOC SA  (http://www.adhoc.com.ar)
#    All Rights Reserved.
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
    'name': 'Account Check Management',
    'version': "1.0.0",
    'category': 'Accounting',
    'summary': 'Checks Management',
    'description': """
Extends 'Check Printing Base' module to:
* allow using own checks that are not printed but filled manually by the user
* allow to use checkbooks to track numbering
* add an optional "payment date" for postdated checks
* add a menu to track own checks

Also implement third checks management
""",
    'author': 'ADHOC SA',
    'license': 'AGPL-3',
    'images': [
    ],
    'depends': [
        'account_check_printing',
    ],
    'data': [
        'data/account_payment_method_data.xml',
        'security/ir.model.access.csv',
        'views/account_payment_view.xml',
        'views/l10n_latam_checkbook_view.xml',
        'views/account_journal_view.xml',
        'wizards/account_payment_register_views.xml',
        'wizards/account_payment_mass_transfer_views.xml',
    ],
    'demo': [
    ],
    'test': [
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
