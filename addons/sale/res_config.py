# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from openerp.osv import fields, osv
from openerp.tools.translate import _

_logger = logging.getLogger(__name__)


class sale_configuration(osv.TransientModel):
    _inherit = 'sale.config.settings'

    _columns = {
        'group_product_variant': fields.selection([
            (0, "No variants on products"),
            (1, 'Products can have several attributes, defining variants (Example: size, color,...)')
            ], "Product Variants",
            help='Work with product variant allows you to define some variant of the same products, an ease the product management in the ecommerce for example',
            implied_group='product.group_product_variant'),
        'module_sale_contract': fields.selection([
            (0, 'Sell based on sales order only'),
            (1, 'Activate contract management to track costs and revenues')
            ], "Contracts",
            help='Allows to define your customer contracts conditions: invoicing '
                 'method (fixed price, on timesheet, advance invoice), the exact pricing '
                 '(650€/day for a developer), the duration (one year support contract).\n'
                 'You will be able to follow the progress of the contract and invoice automatically.\n'
                 '-It installs the sale_contract module.'),
        'group_sale_pricelist':fields.selection([
            (0, 'Set a fixed sale price on each product'),
            (1, 'Use pricelists to adapt your price per customers or products')
            ], "Pricelists",
            implied_group='product.group_sale_pricelist',
            help="""Allows to manage different prices based on rules per category of customers.
                    Example: 10% for retailers, promotion of 5 EUR on this product, etc."""),
        'group_uom':fields.selection([
            (0, 'Products have only one unit of measure (easier)'),
            (1, 'Some products may be sold/purchased in different unit of measures (advanced)')
            ], "Unit of Measures",
            implied_group='product.group_uom',
            help="""Allows you to select and maintain different units of measure for products."""),
        'group_discount_per_so_line': fields.selection([
            (0, 'No discount on sales order lines, global discount only'),
            (1, 'Allow discounts on sales order lines')
            ], "Discount",
            implied_group='sale.group_discount_per_so_line'),
        'group_display_incoterm':fields.selection([
            (0, 'No incoterm on reports'),
            (1, 'Show incoterms on sale orders and invoices')
            ], "Incoterms",
            implied_group='sale.group_display_incoterm',
            help="The printed reports will display the incoterms for the sale orders and the related invoices"),
        'module_sale_margin': fields.selection([
            (0, 'Salespeople do not need to view margins when quoting'),
            (1, 'Display margins on quotations and sales orders')
            ], "Margins"),
        'module_website_sale_digital': fields.selection([
            (0, 'No digital products'),
            (1, 'Allows to sell downloadable content from the portal')
            ], "Digital Products"),
        'module_website_quote': fields.selection([
            (0, 'Print quotes or send by email'),
            (1, 'Send online quotations based on templates (advanced)')
            ], "Online Quotations"),
        'group_sale_delivery_address': fields.selection([
            (0, "Invoicing and shipping addresses are always the same (Example: services companies)"),
            (1, 'Have 3 fields on sales orders: customer, invoice address, delivery address')
            ], "Customer Addresses",
            implied_group='sale.group_delivery_invoice_address'),
    }

    def set_sale_defaults(self, cr, uid, ids, context=None):
        return {}

class account_config_settings(osv.osv_memory):
    _inherit = 'account.config.settings'
    _columns = {
        'group_analytic_account_for_sales': fields.boolean('Analytic accounting for sales',
            implied_group='sale.group_analytic_accounting',
            help="Allows you to specify an analytic account on sales orders."),
    }
