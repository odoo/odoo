# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv
from openerp.tools.translate import _

class purchase_config_settings(osv.osv_memory):
    _name = 'purchase.config.settings'
    _inherit = 'res.config.settings'

    _columns = {
        'default_invoice_method': fields.selection(
            [('manual', 'Control supplier bill on purchase order line'),
             ('picking', 'Control supplier bill on incoming shipments'),
             ('order', 'Control supplier bill on a pregenerated draft invoice'),
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
        'module_purchase_requisition': fields.boolean("Manage calls for tenders",
            help="""Calls for tenders are used when you want to generate requests for quotations to several suppliers for a given set of products.
            You can configure per product if you directly do a Request for Quotation
            to one supplier or if you want a Call for Tenders to compare offers from several suppliers."""),
        'group_advance_purchase_requisition': fields.boolean("Choose from several bids in a call for tenders",
            implied_group='purchase.group_advance_bidding',
            help="""In the process of a public tendering, you can compare the tender lines and choose for each requested product which quantity you will buy from each bid."""),
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


class account_config_settings(osv.osv_memory):
    _inherit = 'account.config.settings'
    _columns = {
        'group_analytic_account_for_purchases': fields.boolean('Analytic accounting for purchases',
            implied_group='purchase.group_analytic_accounting',
            help="Allows you to specify an analytic account on purchase order lines."),
    }
