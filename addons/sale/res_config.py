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

from osv import fields, osv
import pooler
from tools.translate import _

class sale_configuration(osv.osv_memory):
    _inherit = 'sale.config.settings'

    _columns = {
        'group_invoice_so_lines': fields.boolean('generate invoices based on the sale order',
            implied_group='sale.group_invoice_so_lines',
            help="To allow your salesman to make invoices for sale order lines using the menu 'Lines to Invoice'."),
        'group_invoice_deli_orders': fields.boolean('generate invoices after and based on delivery orders',
            implied_group='sale.group_invoice_deli_orders',
            help="To allow your salesman to make invoices for Delivery Orders using the menu 'Deliveries to Invoice'."),
        'task_work': fields.boolean("prepare invoices based on task's activities",
            help="""Lets you transfer the entries under tasks defined for Project Management to
                the Timesheet line entries for particular date and particular user  with the effect of creating, editing and deleting either ways
                and to automatically creates project tasks from procurement lines.
                This installs the modules project_timesheet and project_mrp."""),
        'timesheet': fields.boolean('prepare invoices based on timesheets',
            help = """For modifying account analytic view to show important data to project manager of services companies.
                You can also view the report of account analytic summary user-wise as well as month wise.
                This installs the module account_analytic_analysis."""),
        'module_account_analytic_analysis': fields.boolean('use contracts management',
            help = """Allows to define your customer contracts conditions: invoicing
            method (fixed price, on timesheet, advance invoice), the exact pricing
            (650€/day for a developer), the duration (one year support contract).
            You will be able to follow the progress of the contract and invoice automatically.
            It installs the account_analytic_analysis module."""),
        'default_order_policy': fields.selection(
            [('manual', 'Invoice Based on Sales Orders'), ('picking', 'Invoice Based on Deliveries')],
            'The default invoicing method is', default_model='sale.order',
            help="You can generate invoices based on sales orders or based on shippings."),
        'module_delivery': fields.boolean('allow adding shipping costs',
            help ="""Allows you to add delivery methods in sale orders and delivery orders.
                You can define your own carrier and delivery grids for prices.
                This installs the module delivery."""),
        'time_unit': fields.many2one('product.uom', 'The default working time unit for services is'),
        'default_picking_policy' : fields.boolean("deliver all at once when all products are available.",
            help = "Sales order by default will be configured to deliver all products at once instead of delivering each product when it is available. This may have an impact on the shipping price."),
        'group_sale_pricelist':fields.boolean("use pricelists to adapt your price per customers",
            implied_group='product.group_sale_pricelist',
            help="""Allows to manage different prices based on rules per category of customers.
                Example: 10% for retailers, promotion of 5 EUR on this product, etc."""),
        'group_uom':fields.boolean("allow using different units of measures",
            implied_group='product.group_uom',
            help="""Allows you to select and maintain different units of measure for products."""),
        'group_sale_delivery_address': fields.boolean("allow a different address for delivery and invoicing ",
            implied_group='sale.group_delivery_invoice_address',
            help="Allows you to specify different delivery and invoice addresses on a sale order."),
        'group_mrp_properties': fields.boolean('product properties on order lines',
            implied_group='sale.group_mrp_properties',
            help="Allows you to tag sale order lines with properties."),
        'group_discount_per_so_line': fields.boolean("allow setting a discount on the sale order lines",
            implied_group='sale.group_discount_per_so_line',
            help="Allows you to apply some discount per sale order line."),
        'group_multiple_shops': fields.boolean("manage multiple shops",
            implied_group='stock.group_locations',
            help="This allows to configure and use multiple shops."),
        'module_warning': fields.boolean("allow configuring alerts by customer or products",
            help="""Allow to configure warnings on products and trigger them when a user wants to sale a given product or a given customer.
            Example: Product: this product is deprecated, do not purchase more than 5.
            Supplier: don't forget to ask for an express delivery."""),
        'module_sale_margin': fields.boolean("display margins on sales orders",
            help="""This adds the 'Margin' on sales order.
                This gives the profitability by calculating the difference between the Unit Price and Cost Price.
                This installs the module sale_margin."""),
        'module_sale_journal': fields.boolean("allow batch invoicing through journals",
            help="""Allows you to categorize your sales and deliveries (picking lists) between different journals,
                and perform batch operations on journals.
                This installs the module sale_journal."""),
        'module_analytic_user_function': fields.boolean("assign user roles per contract",
            help="""Allows you to define what is the default function of a specific user on a given account.
                This is mostly used when a user encodes his timesheet. The values are retrieved and the fields are auto-filled.
                But the possibility to change these values is still available.
                This installs the module analytic_user_function."""),
        'module_project_timesheet': fields.boolean("Project Timesheet"),
        'module_project_mrp': fields.boolean("Project MRP"),
        'module_project': fields.boolean("Project"),
        'decimal_precision': fields.integer("Decimal precision on prices:",help="As an example, a decimal precision of 2 will allow prices  like: 9.99 EUR, whereas a decimal precision of 4 will allow prices like:  0.0231 EUR per unit."),
    }
    def _check_decimal(self, cr, uid, ids, context=None):
        for decimal in self.browse(cr, uid, ids, context=context):
            if decimal.decimal_precision > 20:
                return False
        return True

    _constraints = [
        (_check_decimal, 'Digits must be between 0 to 20 ', ['decimal_precision']),
    ]

    def default_get(self, cr, uid, fields, context=None):
        ir_model_data = self.pool.get('ir.model.data')
        res = super(sale_configuration, self).default_get(cr, uid, fields, context)
        # task_work, time_unit depend on other fields
        res['task_work'] = res.get('module_project_mrp') and res.get('module_project_timesheet')
        if res.get('module_project'):
            user = self.pool.get('res.users').browse(cr, uid, uid, context)
            res['time_unit'] = user.company_id.project_time_mode_id.id
        else:
            product = ir_model_data.get_object(cr, uid, 'product', 'product_product_consultant')
            res['time_unit'] = product.uom_id.id
        return res

    def get_default_sale_config(self, cr, uid, ids, context=None):
        ir_values = self.pool.get('ir.values')
        default_picking_policy = ir_values.get_default(cr, uid, 'sale.order', 'picking_policy')
        return {
            'default_picking_policy': default_picking_policy == 'one',
        }

    def _get_default_time_unit(self, cr, uid, context=None):
        ids = self.pool.get('product.uom').search(cr, uid, [('name', '=', _('Hour'))], context=context)
        return ids and ids[0] or False

    _defaults = {
        'default_order_policy': 'manual',
        'time_unit': _get_default_time_unit,
    }

    def get_default_dp(self, cr, uid, fields, context=None):
        dp = self.pool.get('ir.model.data').get_object(cr, uid, 'product','decimal_sale')
        return {'decimal_precision': dp.digits}

    def set_default_dp(self, cr, uid, ids, context=None):
        config = self.browse(cr, uid, ids[0], context)
        dp = self.pool.get('ir.model.data').get_object(cr, uid, 'product','decimal_sale')
        dp.write({'digits': config.decimal_precision})

    def set_sale_defaults(self, cr, uid, ids, context=None):
        ir_values = self.pool.get('ir.values')
        ir_model_data = self.pool.get('ir.model.data')
        wizard = self.browse(cr, uid, ids)[0]

        default_picking_policy = 'one' if wizard.default_picking_policy else 'direct'
        ir_values.set_default(cr, uid, 'sale.order', 'picking_policy', default_picking_policy)

        if wizard.time_unit:
            product = ir_model_data.get_object(cr, uid, 'product', 'product_product_consultant')
            product.write({'uom_id': wizard.time_unit.id, 'uom_po_id': wizard.time_unit.id})

        if wizard.module_project and wizard.time_unit:
            user = self.pool.get('res.users').browse(cr, uid, uid, context)
            user.company_id.write({'project_time_mode_id': wizard.time_unit.id})

        return {}

    def onchange_invoice_methods(self, cr, uid, ids, group_invoice_so_lines, group_invoice_deli_orders, context=None):
        if not group_invoice_deli_orders:
            return {'value': {'default_order_policy': 'manual'}}
        if not group_invoice_so_lines:
            return {'value': {'default_order_policy': 'picking'}}
        return {}

    def onchange_task_work(self, cr, uid, ids, task_work, context=None):
        return {'value': {
            'module_project_timesheet': task_work,
            'module_project_mrp': task_work,
        }}

    def onchange_timesheet(self, cr, uid, ids, timesheet, context=None):
        return {'value': {
            'timesheet': timesheet,
            'module_account_analytic_analysis': timesheet,
        }}



class account_config_settings(osv.osv_memory):
    _inherit = 'account.config.settings'
    _columns = {
        'module_sale_analytic_plans': fields.boolean('several analytic accounts on sales',
            help="""This allows install module sale_analytic_plans."""),
        'group_analytic_account_for_sales': fields.boolean('analytic accounting for sales',
            implied_group='sale.group_analytic_accounting',
            help="Allows you to specify an analytic account on sale orders."),
    }

    def onchange_sale_analytic_plans(self, cr, uid, ids, module_sale_analytic_plans, context=None):
        """ change group_analytic_account_for_sales following module_sale_analytic_plans """
        return {'value': {'group_analytic_account_for_sales': module_sale_analytic_plans}}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
