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
    'name': 'Initial Setup Tools',
    'version': '1.0',
    'category': 'Hidden',
    'description': """
This module helps to configure the system at the installation of a new database.
================================================================================

Shows you a list of applications features to install from.

    """,
    'author': 'OpenERP SA',
    'website': 'https://www.odoo.com',
    'depends': ['base', 'web_kanban'],
    'data': [
        'security/ir.model.access.csv',
        'base_setup_views.xml',
        'res_config_view.xml',
        'res_partner_view.xml',
        'views/base_setup.xml',
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'images': ['images/base_setup1.jpeg','images/base_setup2.jpeg','images/base_setup3.jpeg','images/base_setup4.jpeg',],
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
