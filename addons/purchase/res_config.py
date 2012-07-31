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

class purchase_config_settings(osv.osv_memory):
    _name = 'purchase.config.settings'
    _inherit = 'res.config.settings'

    _columns = {
        'default_invoice_method': fields.selection(
            [('manual', 'Based on Purchase Order Lines'),
             ('picking', 'Based on Receptions'),
             ('order', 'Pre-Generate Draft Invoices based on Purchase Orders'),
            ], 'default invoicing control method', required=True, default_model='purchase.order'),
        'group_purchase_pricelist':fields.boolean("manage pricelist per supplier",
            implied_group='product.group_purchase_pricelist',
            help="""Allows to manage different prices based on rules per category of Supplier.
                Example: 10% for retailers, promotion of 5 EUR on this product, etc."""),
        'group_uom':fields.boolean("manage different units of measures for products",
            implied_group='product.group_uom',
            help="""Allows you to select and maintain different units of measure for products."""),
        'group_purchase_delivery_address': fields.boolean("allow a different address for incoming products and invoicing",
            implied_group='purchase.group_delivery_invoice_address',
            help="Allows you to specify different delivery and invoice addresses on a purchase order."),
        'module_purchase_analytic_plans': fields.boolean('use multiple analytic accounts on orders',
            help ="""Allows the user to maintain several analysis plans. These let you split
                lines on a purchase order between several accounts and analytic plans.
                This installs the module purchase_analytic_plans."""),
        'module_warning': fields.boolean("alerts by products or supllier",
            help="""Allow to configure warnings on products and trigger them when a user wants to purchase a given product or a given supplier.
            Example: Product: this product is deprecated, do not purchase more than 5.
                    Supplier: don't forget to ask for an express delivery."""),

        'module_purchase_double_validation': fields.boolean("force two levels of approvals (limit to require a second approval)",
            help="""Provide a double validation mechanism for purchases exceeding minimum amount.
                This installs the module purchase_double_validation."""),
        'module_purchase_requisition': fields.boolean("manage purchase requisitions",
            help="""Purchase Requisitions are used when you want to request quotations from several suppliers for a given set of products.
            You can configure per product if you directly do a Request for Quotation
            to one supplier or if you want a purchase requisition to negotiate with several suppliers."""),
        'decimal_precision': fields.integer('specify decimal precision on price',help="As an example, a decimal precision of 2 will allow prices   like: 9.99 EUR, whereas a decimal precision of 4 will allow prices  like:  0.0231 EUR per unit."),
    }

    _defaults = {
        'default_invoice_method': 'manual',
    }

    def get_default_dp(self, cr, uid, fields, context=None):
        dp = self.pool.get('ir.model.data').get_object(cr,uid, 'product','decimal_purchase')
        return {'decimal_precision': dp.digits}

    def set_default_dp(self, cr, uid, ids, context=None):
        config = self.browse(cr, uid, ids[0], context)
        dp = self.pool.get('ir.model.data').get_object(cr,uid, 'product','decimal_purchase')
        dp.write({'digits': config.decimal_precision})



class account_config_settings(osv.osv_memory):
    _inherit = 'account.config.settings'
    _columns = {
        'module_purchase_analytic_plans': fields.boolean('use multiple analytic accounts on orders',
            help="""This allows install module purchase_analytic_plans."""),
        'group_analytic_account_for_purchases': fields.boolean('Analytic Accounting for Purchases',
            implied_group='purchase.group_analytic_accounting',
            help="Allows you to specify an analytic account on purchase orders."),
    }

    def onchange_purchase_analytic_plans(self, cr, uid, ids, module_purchase_analytic_plans, context=None):
        """ change group_analytic_account_for_purchases following module_purchase_analytic_plans """
        return {'value': {'group_analytic_account_for_purchases': module_purchase_analytic_plans}}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
