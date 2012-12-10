# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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
    'name': 'Decimal Precision Configuration',
    'description': """
Configure the price accuracy you need for different kinds of usage: accounting, sales, purchases.
=================================================================================================

The decimal precision is configured per company.
""",
    'author': 'OpenERP SA',
    'version': '0.1',
    'depends': ['base'],
    'category' : 'Hidden/Dependency',
    'data': [
        'decimal_precision_view.xml',
        'security/ir.model.access.csv',
    ],
    'demo': [],
    'installable': True,
    'images': ['images/1_decimal_accuracy_form.jpeg','images/1_decimal_accuracy_list.jpeg'],
}



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
