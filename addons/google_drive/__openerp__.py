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
    'name': 'Google Drive™ integration',
    'version': '0.2',
    'author': 'OpenERP SA',
    'website': 'https://www.odoo.com',
    'category': 'Tools',
    'installable': True,
    'auto_install': False,
    'data': [
        'security/ir.model.access.csv',
        'res_config_user_view.xml',
        'google_drive_data.xml',
        'views/google_drive.xml',
    ],
    'demo': [
        'google_drive_demo.xml'
    ],
    'depends': ['base_setup', 'google_account'],
    'description': """
Integrate google document to OpenERP record.
============================================

This module allows you to integrate google documents to any of your OpenERP record quickly and easily using OAuth 2.0 for Installed Applications,
You can configure your google Authorization Code from Settings > Configuration > General Settings by clicking on "Generate Google Authorization Code"
"""
}
