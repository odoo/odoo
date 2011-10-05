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
    'name': 'Display Warning Messages',
    'version': '1.0',
    'category': 'Hidden',
    'complexity': "easy",
    'description': """
Module to trigger warnings in OpenERP objects.
==============================================

Warning messages can be displayed for objects like sale order, purchase order,
picking and invoice. The message is triggered by the form's onchange event.
    """,
    'author': 'OpenERP SA',
    'depends': ['base', 'sale', 'purchase'],
    'update_xml': ['warning_view.xml'],
    'demo_xml': [],
    'installable': True,
    'active': False,
    'certificate': '0080334018749',
    'images': ['images/customers_warnings.jpeg','images/sale_order_warning.jpeg'],
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
