# -*- coding: utf-8 -*-
##############################################################################
#
#    Account reversal module for OpenERP
#    Copyright (C) 2011 Akretion (http://www.akretion.com). All Rights Reserved
#    @author Alexis de Lattre <alexis.delattre@akretion.com>
#    Copyright 2012-2013 Camptocamp SA
#    @author Guewen Baconnier (Camptocamp)
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
    'name': 'Account Reversal',
    'version': '1.0',
    'category': 'Generic Modules/Accounting',
    'license': 'AGPL-3',
    'description': """
Account Reversal
================

This module adds an action "Reversal" on account moves,
to allow the accountant to create reversal account moves in 2 clicks.
Also add on account entries:
 - a checkbox and filter "to be reversed"
 - a link between an entry and its reversal entry

Module originally developped by Alexis de Lattre <alexis.delattre@akretion.com>
during the Akretion-Camptocamp code sprint of June 2011.

""",
    'author': 'Akretion,Camptocamp',
    'website': 'http://www.akretion.com/',
    'depends': ['account'],
    'data': [
        'account_view.xml',
        'wizard/account_move_reverse_view.xml'
        ],
    'installable': True,
    'active': False,
}
