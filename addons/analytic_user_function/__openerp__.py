# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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
    'name': 'Analytic User Function',
    'version': '1.0',
    'category': 'Generic Modules/Others',
    'description': """
This module allows you to define what is the default function of a specific user on a given account.
====================================================================================================

This is mostly used when a user encodes his timesheet: the values are retrieved and the fields are auto-filled. But the possibility to change these values is still available.

Obviously if no data has been recorded for the current account, the default value is given as usual by the employee data so that this module is perfectly compatible with older configurations.

    """,
    'author': 'OpenERP SA',
    'website': 'http://www.openerp.com',
    'images': ['images/analytic_user_function.jpeg'],
    'depends': ['hr_timesheet_sheet'],
    'init_xml': [],
    'update_xml': ['analytic_user_function_view.xml', 'security/ir.model.access.csv'],
    'demo_xml': [],
    'installable': True,
    'active': False,
    'certificate': '0082277138269',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
