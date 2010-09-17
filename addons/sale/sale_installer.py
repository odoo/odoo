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
from osv import fields, osv

class sale_installer(osv.osv_memory):
    _name = 'sale.installer'
    _inherit = 'res.config.installer'

    _columns = {
        'sale_analytic_plans': fields.boolean('Sales Analytic Distribution Management',
            help="The base module to manage analytic distribution and sales orders."),
        'sale_journal': fields.boolean('Sales and deliveries by journal',
            help="The sale journal modules allows you to categorise your "
                "sales and deliveries (picking lists) between different journals. "
                "This module is very helpful for bigger companies that "
                "works by departments."),
        'sale_layout': fields.boolean('Sale Order Layout Improvement',
            help="This module provides some features to improve the layout of the Sale Order."),
        'sale_margin': fields.boolean('Margins in Sale Orders',
            help="This module adds the 'Margin' on sales order, "
                "which gives the profitability by calculating "
                "the difference between the Unit Price and Cost Price."),
        'sale_order_dates': fields.boolean('Sale Order Dates',
            help="Add commitment, requested and effective dates on the sale order."),
        }
sale_installer()
