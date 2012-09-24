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
    'name': 'Google Docs integration',
    'version': '0.2',
    'author': 'OpenERP SA',
    'website': 'http://openerp.com',
    'category': 'Tools',
    'installable': True,
    'auto_install': False,
    'web': True,
    'js': ['static/src/js/gdocs.js'],
    'data': [
        'security/ir.model.access.csv',
        'res_config_user_view.xml'
    ],
    'depends': ['google_base_account'],
    'description': """
Module to attach a google document to any model.
================================================
"""
}
