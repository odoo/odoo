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
    'name': 'Enterprise Process',
    'version': '1.0',
    'category': 'Hidden/Dependency',
    'description': """
This module shows the basic processes involved in the selected modules and in the sequence they occur.
======================================================================================================

Note: This applies to the modules containing modulename_process.xml.
e.g product/process/product_process.xml.

    """,
    'author': 'OpenERP SA',
    'website': 'http://www.openerp.com',
    'depends': ['base'],
    'data': [],
    'data': [
       'security/ir.model.access.csv',
       'process_view.xml'
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'certificate': '0055447636669',
    'images': ['images/process_nodes.jpeg','images/process_transitions.jpeg', 'images/processes.jpeg'],
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
