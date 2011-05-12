# -*- coding: utf-8 -*-
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
from osv import fields, osv

class mrp_installer(osv.osv_memory):
    _inherit = 'base.setup.installer'

    _columns = {
        # Manufacturing Resource Planning
        'stock_location': fields.boolean('Advanced Routes',
            help="Manages product routes and paths within and between "
                 "locations (e.g. warehouses)."),
        'mrp_jit': fields.boolean('Just In Time Scheduling',
            help="Enables Just In Time computation of procurement orders."
                 "\n\nWhile it's more resource intensive than the default "
                 "setup, the JIT computer avoids having to wait for the "
                 "procurement scheduler to run or having to run the "
                 "procurement scheduler manually."),
        'mrp_operations': fields.boolean('Manufacturing Operations',
            help="Enhances production orders with readiness states as well "
                 "as the start date and end date of execution of the order."),
        'mrp_subproduct': fields.boolean('MRP Subproducts',
            help="Enables multiple product output from a single production "
                 "order: without this, a production order can have only one "
                 "output product."),
        'mrp_repair': fields.boolean('Repairs',
            help="Enables warranty and repair management (and their impact "
                 "on stocks and invoicing)."),
        }

    _defaults = {
        'mrp_jit': lambda self,cr,uid,*a: self.pool.get('res.users').browse(cr, uid, uid).view == 'simple',
    }
mrp_installer()
