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

class product_groups_configuration(osv.osv_memory):
    _inherit = 'res.config'

    _columns = {
        'group_sale_pricelist_per_customer':fields.boolean("Pricelist per customer ",
                                                           help="""
                                                           Allows to manage different prices based on rules per category of customers. Example: 10% for retailers, promotion of 5 EUR on this product,
                                                           It assigns the "pricelist" group to all employees
                                                           """),
        'group_sale_uom_per_product':fields.boolean("UOM per product",
                                                    help="""
                                                    This allow different unit of measure per product,
                                                    It assigns the "UOM per product" group to all employees
                                                    """),
}

product_groups_configuration()