# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from openerp.osv import fields, osv

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
        'group_sale_pricelist':fields.boolean("Use pricelists to adapt your price per customers",implied_group='product.group_sale_pricelist',
            help="""Allows to manage different prices based on rules per category of customers.
                    Example: 10% for retailers, promotion of 5 EUR on this product, etc."""),
        'group_pricelist_item':fields.boolean("Show pricelists to customers", implied_group='product.group_pricelist_item'),
        'group_product_pricelist':fields.boolean("Show pricelists On Products", implied_group='product.group_product_pricelist'),
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
        'module_website_quote': fields.selection([
            (0, 'Print quotes or send by email'),
            (1, 'Send online quotations based on templates (advanced)')
            ], "Online Quotations"),
        'group_sale_delivery_address': fields.selection([
            (0, "Invoicing and shipping addresses are always the same (Example: services companies)"),
            (1, 'Display 3 fields on sales orders: customer, invoice address, delivery address')
            ], "Addresses", implied_group='sale.group_delivery_invoice_address'),
        'sale_pricelist_setting': fields.selection([('fixed', 'A single sale price per product'), ('percentage', 'Different prices per customer segment'), ('formula', 'Advanced pricing based on formula')], required=True,
        help='Fix Price: all price manage from products sale price.\n'
             'Different prices per Customer: you can assign price on buying of minimum quantity in products sale tab.\n'
             'Advanced pricing based on formula: You can have all the rights on pricelist'),
        'default_invoice_policy': fields.selection([
            ('order', 'Invoice ordered quantities'),
            ('delivery', 'Invoice delivered quantities'),
            ('cost', 'Invoice based on costs (time and material, expenses)')
            ], 'Default Invoicing', default_model='product.template'),
        'deposit_product_id_setting': fields.many2one('product.product', 'Deposit Product',\
            domain="[('type', '=', 'service')]",\
            help='Default product used for payment advances'),
        'auto_done_setting': fields.selection([
            (0, "Allow to edit sales order from the 'Sales Order' menu (not from the Quotation menu)"),
            (1, "Never allow to modify a confirmed sale order")
            ], "Sale Order Modification"),
        'module_sale_contract': fields.boolean("Manage subscriptions and recurring invoicing"),
        'module_website_sale_digital': fields.boolean("Sell digital products - provide downloadable content on your customer portal"),
        'module_website_portal': fields.boolean("Enable customer portal to track orders, delivery and invoices"),
    }

    _defaults = {
        'sale_pricelist_setting': 'fixed',
        'default_invoice_policy': 'order',
    }

    def set_sale_defaults(self, cr, uid, ids, context=None):
        sale_price = self.browse(cr, uid, ids, context=context).sale_pricelist_setting
        res = self.pool.get('ir.values').set_default(cr, uid, 'sale.config.settings', 'sale_pricelist_setting', sale_price)
        return res

    def set_deposit_product_id_defaults(self, cr, uid, ids, context=None):
        deposit_product_id = self.browse(cr, uid, ids, context=context).deposit_product_id_setting
        res = self.pool.get('ir.values').set_default(cr, uid, 'sale.config.settings', 'deposit_product_id_setting', deposit_product_id.id)
        return res

    def set_auto_done_defaults(self, cr, uid, ids, context=None):
        auto_done = self.browse(cr, uid, ids, context=context).auto_done_setting
        res = self.pool.get('ir.values').set_default(cr, uid, 'sale.config.settings', 'auto_done_setting', auto_done)
        return res

    def onchange_sale_price(self, cr, uid, ids, sale_pricelist_setting, context=None):
        if sale_pricelist_setting == 'percentage':
            return {'value': {'group_product_pricelist': True, 'group_sale_pricelist': True, 'group_pricelist_item': False}}
        if sale_pricelist_setting == 'formula':
            return {'value': {'group_pricelist_item': True, 'group_sale_pricelist': True, 'group_product_pricelist': False}}
        return {'value': {'group_pricelist_item': False, 'group_sale_pricelist': False, 'group_product_pricelist': False}}


class account_config_settings(osv.osv_memory):
    _inherit = 'account.config.settings'
    _columns = {
        'group_analytic_account_for_sales': fields.boolean('Analytic accounting for sales',
            implied_group='sale.group_analytic_accounting',
            help="Allows you to specify an analytic account on sales orders."),
    }
