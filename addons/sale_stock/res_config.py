# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (C) 2004-2012 OpenERP S.A. (<http://openerp.com>).
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

import openerp
from openerp import SUPERUSER_ID
from openerp.osv import fields, osv
from openerp.tools.translate import _

class sale_configuration(osv.osv_memory):
    _inherit = 'sale.config.settings'

    _columns = {
        'group_invoice_deli_orders': fields.boolean('Generate invoices after and based on delivery orders',
            implied_group='sale_stock.group_invoice_deli_orders',
            help="To allow your salesman to make invoices for Delivery Orders using the menu 'Deliveries to Invoice'."),
        'task_work': fields.boolean("Prepare invoices based on task's activities",
            help='Lets you transfer the entries under tasks defined for Project Management to '
                 'the Timesheet line entries for particular date and particular user  with the effect of creating, editing and deleting either ways '
                 'and to automatically creates project tasks from procurement lines.\n'
                 '-This installs the modules project_timesheet and sale_service.'),
        'default_order_policy': fields.selection(
            [('manual', 'Invoice based on sales orders'), ('picking', 'Invoice based on deliveries')],
            'The default invoicing method is', default_model='sale.order',
            help="You can generate invoices based on sales orders or based on shippings."),
        'module_delivery': fields.boolean('Allow adding shipping costs',
            help='Allows you to add delivery methods in sales orders and delivery orders.\n'
                 'You can define your own carrier and delivery grids for prices.\n'
                 '-This installs the module delivery.'),
        'default_picking_policy' : fields.boolean("Deliver all at once when all products are available.",
            help = "Sales order by default will be configured to deliver all products at once instead of delivering each product when it is available. This may have an impact on the shipping price."),
        'group_mrp_properties': fields.boolean('Product properties on order lines',
            implied_group='sale.group_mrp_properties',
            help="Allows you to tag sales order lines with properties."),
        'module_project_timesheet': fields.boolean("Project Timesheet"),
        'module_sale_service': fields.boolean("Sale Service"),
        'group_route_so_lines': fields.boolean('Choose MTO, drop shipping,... on sales order lines',
            implied_group='sale_stock.group_route_so_lines',
            help="Allows you to choose a delivery route on sales order lines"),
    }

    _defaults = {
        'default_order_policy': 'manual',
    }

    def default_get(self, cr, uid, fields, context=None):
        res = super(sale_configuration, self).default_get(cr, uid, fields, context)
        # task_work, time_unit depend on other fields
        res['task_work'] = res.get('module_sale_service') and res.get('module_project_timesheet')
        return res

    def get_default_sale_config(self, cr, uid, ids, context=None):
        ir_values = self.pool.get('ir.values')
        default_picking_policy = ir_values.get_default(cr, uid, 'sale.order', 'picking_policy')
        return {
            'default_picking_policy': default_picking_policy == 'one',
        }

    def set_sale_defaults(self, cr, uid, ids, context=None):
        if uid != SUPERUSER_ID and not self.pool['res.users'].has_group(cr, uid, 'base.group_erp_manager'):
            raise openerp.exceptions.AccessError(_("Only administrators can change the settings"))
        ir_values = self.pool.get('ir.values')
        wizard = self.browse(cr, uid, ids)[0]

        default_picking_policy = 'one' if wizard.default_picking_policy else 'direct'
        ir_values.set_default(cr, SUPERUSER_ID, 'sale.order', 'picking_policy', default_picking_policy)
        res = super(sale_configuration, self).set_sale_defaults(cr, uid, ids, context)
        return res

    def onchange_invoice_methods(self, cr, uid, ids, group_invoice_so_lines, group_invoice_deli_orders, context=None):
        if not group_invoice_deli_orders:
            return {'value': {'default_order_policy': 'manual'}}
        if not group_invoice_so_lines:
            return {'value': {'default_order_policy': 'picking'}}
        return {}
