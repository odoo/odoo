# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#    Copyright (C) 2010-2012 OpenERP s.a. (<http://openerp.com>).
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
    'name': 'Dashboards',
    'version': '1.0',
    'category': 'Hidden',
    'description': """
Lets the user create a custom dashboard.
========================================

This module also creates the Administration Dashboard.

The user can also publish notes.
    """,
    'author': 'OpenERP SA',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'board_view.xml',
        'board_mydashboard_view.xml'
    ],
    'js': [
        'static/src/js/dashboard.js',
    ],
    'css': [
        'static/src/css/dashboard.css',
    ],
    'qweb': [
        'static/src/xml/*.xml',
    ],

    'installable': True,
    'auto_install': False,
    'certificate': '0076912305725',
    'images': ['images/1_dashboard_definition.jpeg','images/2_publish_note.jpeg','images/3_admin_dashboard.jpeg',],
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
