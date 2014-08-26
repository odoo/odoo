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

import logging

from openerp.osv import fields, osv
from openerp.tools.translate import _

_logger = logging.getLogger(__name__)


class sale_configuration(osv.TransientModel):
    _inherit = 'sale.config.settings'

    _columns = {
        'group_invoice_so_lines': fields.boolean('Generate invoices based on the sales order lines',
            implied_group='sale.group_invoice_so_lines',
            help="To allow your salesman to make invoices for sales order lines using the menu 'Lines to Invoice'."),
        'timesheet': fields.boolean('Prepare invoices based on timesheets',
            help='For modifying account analytic view to show important data to project manager of services companies.'
                 'You can also view the report of account analytic summary user-wise as well as month wise.\n'
                 '-This installs the module account_analytic_analysis.'),
        'module_account_analytic_analysis': fields.boolean('Use contracts management',
            help='Allows to define your customer contracts conditions: invoicing '
                 'method (fixed price, on timesheet, advance invoice), the exact pricing '
                 '(650€/day for a developer), the duration (one year support contract).\n'
                 'You will be able to follow the progress of the contract and invoice automatically.\n'
                 '-It installs the account_analytic_analysis module.'),
        'time_unit': fields.many2one('product.uom', 'The default working time unit for services is'),
        'group_sale_pricelist':fields.boolean("Use pricelists to adapt your price per customers",
            implied_group='product.group_sale_pricelist',
            help="""Allows to manage different prices based on rules per category of customers.
Example: 10% for retailers, promotion of 5 EUR on this product, etc."""),
        'group_uom':fields.boolean("Allow using different units of measure",
            implied_group='product.group_uom',
            help="""Allows you to select and maintain different units of measure for products."""),
        'group_discount_per_so_line': fields.boolean("Allow setting a discount on the sales order lines",
            implied_group='sale.group_discount_per_so_line',
            help="Allows you to apply some discount per sales order line."),
        'module_warning': fields.boolean("Allow configuring alerts by customer or products",
            help='Allow to configure notification on products and trigger them when a user wants to sell a given product or a given customer.\n'
                 'Example: Product: this product is deprecated, do not purchase more than 5.\n'
                 'Supplier: don\'t forget to ask for an express delivery.'),
        'module_sale_margin': fields.boolean("Display margins on sales orders",
            help='This adds the \'Margin\' on sales order.\n'
                 'This gives the profitability by calculating the difference between the Unit Price and Cost Price.\n'
                 '-This installs the module sale_margin.'),
        'module_website_quote': fields.boolean("Allow online quotations and templates",
            help='This adds the online quotation'),
        'module_sale_journal': fields.boolean("Allow batch invoicing of delivery orders through journals",
            help='Allows you to categorize your sales and deliveries (picking lists) between different journals, '
                 'and perform batch operations on journals.\n'
                 '-This installs the module sale_journal.'),
        'module_analytic_user_function': fields.boolean("One employee can have different roles per contract",
            help='Allows you to define what is the default function of a specific user on a given account.\n'
                 'This is mostly used when a user encodes his timesheet. The values are retrieved and the fields are auto-filled. '
                 'But the possibility to change these values is still available.\n'
                 '-This installs the module analytic_user_function.'),
        'module_project': fields.boolean("Project"),
        'module_sale_stock': fields.boolean("Trigger delivery orders automatically from sales orders",
            help='Allows you to Make Quotation, Sale Order using different Order policy and Manage Related Stock.\n'
                 '-This installs the module sale_stock.'),
        'group_sale_delivery_address': fields.boolean("Allow a different address for delivery and invoicing ",
            implied_group='sale.group_delivery_invoice_address',
            help="Allows you to specify different delivery and invoice addresses on a sales order."),
    }

    def default_get(self, cr, uid, fields, context=None):
        ir_model_data = self.pool.get('ir.model.data')
        res = super(sale_configuration, self).default_get(cr, uid, fields, context)
        if res.get('module_project'):
            user = self.pool.get('res.users').browse(cr, uid, uid, context)
            res['time_unit'] = user.company_id.project_time_mode_id.id
        else:
            product = ir_model_data.xmlid_to_object(cr, uid, 'product.product_product_consultant')
            if product and product.exists():
                res['time_unit'] = product.uom_id.id
        res['timesheet'] = res.get('module_account_analytic_analysis')
        return res

    def _get_default_time_unit(self, cr, uid, context=None):
        ids = self.pool.get('product.uom').search(cr, uid, [('name', '=', _('Hour'))], context=context)
        return ids and ids[0] or False

    _defaults = {
        'time_unit': _get_default_time_unit,
    }

    def set_sale_defaults(self, cr, uid, ids, context=None):
        ir_model_data = self.pool.get('ir.model.data')
        wizard = self.browse(cr, uid, ids)[0]

        if wizard.time_unit:
            product = ir_model_data.xmlid_to_object(cr, uid, 'product.product_product_consultant')
            if product and product.exists():
                product.write({'uom_id': wizard.time_unit.id, 'uom_po_id': wizard.time_unit.id})
            else:
                _logger.warning("Product with xml_id 'product.product_product_consultant' not found, UoMs not updated!")

        if wizard.module_project and wizard.time_unit:
            user = self.pool.get('res.users').browse(cr, uid, uid, context)
            user.company_id.write({'project_time_mode_id': wizard.time_unit.id})
        return {}

    def onchange_task_work(self, cr, uid, ids, task_work, context=None):
        return {'value': {
            'module_project_timesheet': task_work,
            'module_sale_service': task_work,
        }}

    def onchange_timesheet(self, cr, uid, ids, timesheet, context=None):
        return {'value': {
            'timesheet': timesheet,
            'module_account_analytic_analysis': timesheet,
        }}

class account_config_settings(osv.osv_memory):
    _inherit = 'account.config.settings'
    _columns = {
        'module_sale_analytic_plans': fields.boolean('Use multiple analytic accounts on sales',
            help="""This allows install module sale_analytic_plans."""),
        'group_analytic_account_for_sales': fields.boolean('Analytic accounting for sales',
            implied_group='sale.group_analytic_accounting',
            help="Allows you to specify an analytic account on sales orders."),
    }

    def onchange_sale_analytic_plans(self, cr, uid, ids, module_sale_analytic_plans, context=None):
        """ change group_analytic_account_for_sales following module_sale_analytic_plans """
        if not module_sale_analytic_plans:
            return {}
        return {'value': {'group_analytic_account_for_sales': module_sale_analytic_plans}}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
