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

from openerp.osv import fields, osv
from openerp.tools.translate import _

class purchase_config_settings(osv.osv_memory):
    _name = 'purchase.config.settings'
    _inherit = 'res.config.settings'

    _columns = {
        'default_invoice_method': fields.selection(
            [('manual', 'Control supplier invoice on purchase order line'),
             ('picking', 'Control supplier invoice on incoming shipments'),
             ('order', 'Control supplier invoice on a pregenerated draft invoice'),
            ], 'Default invoicing control method', required=True, default_model='purchase.order'),
        'group_purchase_pricelist':fields.boolean("Manage pricelist per supplier",
            implied_group='product.group_purchase_pricelist',
            help='Allows to manage different prices based on rules per category of Supplier.\n'
                 'Example: 10% for retailers, promotion of 5 EUR on this product, etc.'),
        'group_uom':fields.boolean("Manage different units of measure for products",
            implied_group='product.group_uom',
            help="""Allows you to select and maintain different units of measure for products."""),
        'group_costing_method':fields.boolean("Use 'Real Price' or 'Average' costing methods.",
            implied_group='stock_account.group_inventory_valuation',
            help="""Allows you to compute product cost price based on average cost."""),
        'module_warning': fields.boolean("Alerts by products or supplier",
            help='Allow to configure notification on products and trigger them when a user wants to purchase a given product or a given supplier.\n'
                 'Example: Product: this product is deprecated, do not purchase more than 5.\n'
                 'Supplier: don\'t forget to ask for an express delivery.'),
        'module_purchase_double_validation': fields.boolean("Force two levels of approvals",
            help='Provide a double validation mechanism for purchases exceeding minimum amount.\n'
                 '-This installs the module purchase_double_validation.'),
        'module_purchase_requisition': fields.boolean("Manage calls for bids",
            help="""Calls for bids are used when you want to generate requests for quotations to several suppliers for a given set of products.
            You can configure per product if you directly do a Request for Quotation
            to one supplier or if you want a Call for Bids to compare offers from several suppliers."""),
        'group_advance_purchase_requisition': fields.boolean("Choose from several bids in a call for bids",
            implied_group='purchase.group_advance_bidding',
            help="""In the process of a public bidding, you can compare the bid lines and choose for each requested product from which bid you
            buy which quantity"""),
        'module_purchase_analytic_plans': fields.boolean('Use multiple analytic accounts on purchase orders',
            help='Allows the user to maintain several analysis plans. These let you split lines on a purchase order between several accounts and analytic plans.\n'
                 '-This installs the module purchase_analytic_plans.'),
        'group_analytic_account_for_purchases': fields.boolean('Analytic accounting for purchases',
            implied_group='purchase.group_analytic_accounting',
            help="Allows you to specify an analytic account on purchase order lines."),
        'module_stock_dropshipping': fields.boolean("Manage dropshipping",
            help='\nCreates the dropship route and add more complex tests'
                 '-This installs the module stock_dropshipping.'),
    }

    _defaults = {
        'default_invoice_method': 'order',
    }

    def onchange_purchase_analytic_plans(self, cr, uid, ids, module_purchase_analytic_plans, context=None):
        """ change group_analytic_account_for_purchases following module_purchase_analytic_plans """
        if not module_purchase_analytic_plans:
            return {}
        return {'value': {'group_analytic_account_for_purchases': module_purchase_analytic_plans}}



class account_config_settings(osv.osv_memory):
    _inherit = 'account.config.settings'
    _columns = {
        'module_purchase_analytic_plans': fields.boolean('Use multiple analytic accounts on orders',
            help='Allows the user to maintain several analysis plans. These let you split lines on a purchase order between several accounts and analytic plans.\n'
                 '-This installs the module purchase_analytic_plans.'),
        'group_analytic_account_for_purchases': fields.boolean('Analytic accounting for purchases',
            implied_group='purchase.group_analytic_accounting',
            help="Allows you to specify an analytic account on purchase order lines."),
    }

    def onchange_purchase_analytic_plans(self, cr, uid, ids, module_purchase_analytic_plans, context=None):
        """ change group_analytic_account_for_purchases following module_purchase_analytic_plans """
        if not module_purchase_analytic_plans:
            return {}
        return {'value': {'group_analytic_account_for_purchases': module_purchase_analytic_plans}}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
