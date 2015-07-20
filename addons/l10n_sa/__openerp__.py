# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2015 Mohamed M. Hagag.
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
    'name': 'Arabic CoA, Saudi Arabia',
    'version': '1.1',
    'sequence': 1,
    'author': 'DVIT.ME',
    'category': 'Localization/Account Charts',
    'description': "Arabic Chart of accounts for Arabic countries and Saudi Arabia.",
    'website': 'http://www.dvit.me',
    'depends': ['account_chart', 'l10n_multilang', 'account_anglo_saxon'],
    'data': [
        'account_type.xml',
        'account.account.template.csv',
        'account.chart.template.xml',
        'wizard.xml',
    ],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
