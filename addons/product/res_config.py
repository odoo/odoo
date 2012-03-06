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
    _inherit = 'res.config.settings'

    _columns = {
        'group_stock_packaging':fields.boolean("Manage packaging by products",group='base.group_user', implied_group='base.group_stock_packaging',
                           help=""" Allows you to create and manage your packaging dimensions and types you want to be maintained in your system.
                           It assigns the "Packaging" group to employee."""),
        'group_stock_uom':fields.boolean("Manage your stock counterpart by products",group='base.group_user', implied_group='base.group_stock_uom',
                           help="""Allows you to create and manage the units of measure you want to be used in your system. You can define a conversion rate between several Units of Measure within the same category.
                           It assigns the "UOM in warehouse" group to employee."""),

}

product_groups_configuration()