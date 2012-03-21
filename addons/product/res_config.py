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

class sale_config_settings(osv.osv_memory):
    _inherit = 'sale.config.settings'

    _columns = {
        'group_sale_pricelist':fields.boolean("Pricelist per Customer",
            implied_group='product.group_sale_pricelist',
            help="""Allows to manage different prices based on rules per category of customers. 
                Example: 10% for retailers, promotion of 5 EUR on this product, etc."""),
        'group_purchase_pricelist':fields.boolean("Pricelist per Supplier",
            implied_group='product.group_purchase_pricelist',
            help="""Allows to manage different prices based on rules per category of Supplier.
                Example: 10% for retailers, promotion of 5 EUR on this product, etc."""),
        'group_sale_uom':fields.boolean("UOM per product",
            implied_group='product.group_uom',
            help="""Allows you to select and maintain different unit of measures per product."""),
        'group_stock_packaging':fields.boolean("Manage packaging by products",
            implied_group='product.group_packaging',
            help=""" Allows you to create and manage your packaging dimensions and types you want to be maintained in your system."""),
}
