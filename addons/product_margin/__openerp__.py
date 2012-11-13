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
    'name': 'Margins by Products',
    'version': '1.0',
    'category': 'Sales Management',
    'description': """
Adds a reporting menu in products that computes sales, purchases, margins and other interesting indicators based on invoices.
=============================================================================================================================

The wizard to launch the report has several options to help you get the data you need.
""",
    'author': 'OpenERP SA',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/product_margin_view.xml',
        'product_margin_view.xml'
    ],
    'test':['test/product_margin.yml'],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'images': ['images/open_margins.jpeg','images/product_margins_form.jpeg', 'images/product_margins_list.jpeg'],
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
