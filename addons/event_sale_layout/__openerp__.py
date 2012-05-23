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
    'name': 'Events Sales layout',
    'version': '0.1',
    'category': 'Tools',
    'description': """
    This module ensures the compatibility of the changes made on the sale.order.line form view in event_sale with the sale_layout module (that is replacing the whole field in the view by another one). Its installation is automatically triggered when both modules are installed.
    """,
    'author': 'OpenERP SA',
    'depends': ['event_sale','sale_layout'],
    'update_xml': [
        'event_sale_layout.xml',
    ],
    'installable': True,
    'auto_install':True,
    'category': 'Hidden',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
