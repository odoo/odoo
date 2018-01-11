# -*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2014 InnOpen Group Kft (<http://www.innopen.eu>).
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
    'name': 'Hungarian - Accounting',
    'version': '1.0',
    'category': 'Localization/Account Charts',
    'description': """

Base module for Hungarian localization
==========================================

This module consists :

 - Generic Hungarian chart of accounts
 - Hungarian taxes
 - Hungarian Bank information
 
 """,
    'author': 'InnOpen Group Kft',
    'website': 'http://www.innopen.eu',
    'license': 'AGPL-3',
    'depends': ['account','account_chart'],
    'data': [
        'data/account.account.template.csv',
        'data/account.tax.code.template.csv',
        'data/account.chart.template.csv',
        'data/account.tax.template.csv',
        'data/account.fiscal.position.template.csv',
        'data/account.fiscal.position.tax.template.csv',
        'data/res.bank.csv',
    ],
    'installable': True,
    'auto_install': False,
}
