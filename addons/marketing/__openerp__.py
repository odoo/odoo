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
    'name': 'Marketing',
    'version': '1.1',
    'depends': ['base', 'base_setup', 'crm'],
    'author': 'OpenERP SA',
    'category': 'Hidden/Dependency',
    'description': """
Menu for Marketing.
===================

Contains the installer for marketing-related modules.
    """,
    'website': 'http://www.openerp.com',
    'data': [
        'security/marketing_security.xml',
        'security/ir.model.access.csv',
        'marketing_view.xml',
        'res_config_view.xml',
    ],
    'demo': ['marketing_demo.xml'],
    'installable': True,
    'auto_install': False,
    'images': ['images/config_marketing.jpeg'],
}
