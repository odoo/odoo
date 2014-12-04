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
    'depends': ['base', 'report'],
    'category' : 'Tools',
    'summary': 'Lunch Order, Meal, Food',
    'description': """
The base module to manage lunch.
================================

Many companies order sandwiches, pizzas and other, from usual suppliers, for their employees to offer them more facilities. 

However lunches management within the company requires proper administration especially when the number of employees or suppliers is important. 

The “Lunch Order” module has been developed to make this management easier but also to offer employees more tools and usability. 

In addition to a full meal and supplier management, this module offers the possibility to display warning and provides quick order selection based on employee’s preferences.

If you want to save your employees' time and avoid them to always have coins in their pockets, this module is essential.
    """,
    'data': [
        'security/lunch_security.xml',
        'lunch_view.xml',
        'wizard/lunch_order_view.xml',
        'wizard/lunch_validation_view.xml',
        'wizard/lunch_cancel_view.xml',
        'lunch_report.xml',
        'report/report_lunch_order_view.xml',
        'security/ir.model.access.csv',
        'views/report_lunchorder.xml',
        'views/lunch.xml',
    ],
    'images': ['images/new_order.jpeg','images/lunch_account.jpeg','images/order_by_supplier_analysis.jpeg','images/alert.jpeg'],
    'demo': ['lunch_demo.xml',],
    'installable': True,
    'website': 'https://www.odoo.com/page/employees',
    'application' : True,
    'certificate' : '001292377792581874189',
    'images': [],
}
