# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2012 Tiny SPRL (<http://tiny.be>).
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
    'name': 'Lunch Orders',
    'author': 'OpenERP SA',
    'version': '0.2',
    'depends': ['base'],
    'category' : 'Tools',
    'description': """
The base module to manage lunch.
================================

keep track for the Lunch Order, Cash Moves and Product. Apply Different
Category for the product.
    """,
    'data': ['security/groups.xml','view/lunch_view.xml','view/partner_view.xml','wizard/lunch_validation_view.xml','wizard/lunch_cancel_view.xml','lunch_report.xml',
        'report/report_lunch_order_view.xml',
        'security/ir.model.access.csv',],
    'demo': ['lunch_demo.xml',],
    'test': [],
    'installable': True,
    'application' : True,
    'certificate' : '001292377792581874189',
    'images': [],
}
