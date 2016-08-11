# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class SaleConfiguration(models.TransientModel):
    _inherit = 'sale.config.settings'

    group_product_variant = fields.Selection([
        (0, "No variants on products"),
        (1, 'Products can have several attributes, defining variants (Example: size, color,...)')
        ], "Product Variants",
        help="""Work with product variant allows you to define some variant of the same products
                , an ease the product management in the ecommerce for example""",
        implied_group='product.group_product_variant')
    group_sale_pricelist = fields.Boolean("Use pricelists to adapt your price per customers",
        implied_group='product.group_sale_pricelist',
        help="""Allows to manage different prices based on rules per category of customers.
                Example: 10% for retailers, promotion of 5 EUR on this product, etc.""")
    group_pricelist_item = fields.Boolean("Show pricelists to customers",
        implied_group='product.group_pricelist_item')
    group_product_pricelist = fields.Boolean("Show pricelists On Products",
        implied_group='product.group_product_pricelist')
    group_uom = fields.Selection([
        (0, 'Products have only one unit of measure (easier)'),
        (1, 'Some products may be sold/purchased in different units of measure (advanced)')
        ], "Units of Measure",
        implied_group='product.group_uom',
        help="""Allows you to select and maintain different units of measure for products.""")
    group_discount_per_so_line = fields.Selection([
        (0, 'No discount on sales order lines, global discount only'),
        (1, 'Allow discounts on sales order lines')
        ], "Discount",
        implied_group='sale.group_discount_per_so_line')
    group_display_incoterm = fields.Selection([
        (0, 'No incoterm on reports'),
        (1, 'Show incoterms on sale orders and invoices')
        ], "Incoterms",
        implied_group='sale.group_display_incoterm',
        help="The printed reports will display the incoterms for the sale orders and the related invoices")
    module_product_visible_discount = fields.Selection([
        (0, 'No discount policy on sale order line'),
        (1, 'Allow discount policy on sale order line')
        ], "Discount Policy")
    module_sale_margin = fields.Selection([
        (0, 'Salespeople do not need to view margins when quoting'),
        (1, 'Display margins on quotations and sales orders')
        ], "Margins")
    group_sale_layout = fields.Selection([
        (0, 'Do not personalize sale orders and invoice reports'),
        (1, 'Personalize the sale orders and invoice report with categories, subtotals and page-breaks')
        ], "Sale Reports Layout", implied_group='sale.group_sale_layout')
    group_warning_sale = fields.Selection([
        (0, 'All the products and the customers can be used in sale orders'),
        (1, 'An informative or blocking warning can be set on a product or a customer')
        ], "Warning", implied_group='sale.group_warning_sale')
    module_website_quote = fields.Selection([
        (0, 'Print quotes or send by email'),
        (1, 'Send online quotations based on templates (advanced)')
        ], "Online Quotations")
    group_sale_delivery_address = fields.Selection([
        (0, "Invoicing and shipping addresses are always the same (Example: services companies)"),
        (1, 'Display 3 fields on sales orders: customer, invoice address, delivery address')
        ], "Addresses", implied_group='sale.group_delivery_invoice_address')
    sale_pricelist_setting = fields.Selection([
        ('fixed', 'A single sale price per product'),
        ('percentage', 'Different prices per customer segment'),
        ('formula', 'Advanced pricing based on formula')
        ], required=True,
        default='fixed',
        help='Fix Price: all price manage from products sale price.\n'
             'Different prices per Customer: you can assign price on buying of minimum quantity in products sale tab.\n'
             'Advanced pricing based on formula: You can have all the rights on pricelist')
    group_show_price_subtotal = fields.Boolean(
        "Show subtotal",
        implied_group='sale.group_show_price_subtotal',
        group='base.group_portal,base.group_user,base.group_public')
    group_show_price_total = fields.Boolean(
        "Show total",
        implied_group='sale.group_show_price_total',
        group='base.group_portal,base.group_user,base.group_public')
    sale_show_tax = fields.Selection([
        ('subtotal', 'Show line subtotals without taxes (B2B)'),
        ('total', 'Show line subtotals with taxes included (B2C)')], "Tax Display",
        default='subtotal',
        required=True)
    default_invoice_policy = fields.Selection([
        ('order', 'Invoice ordered quantities'),
        ('delivery', 'Invoice delivered quantities')
        ], 'Default Invoicing',
        default='order',
        default_model='product.template')
    deposit_product_id_setting = fields.Many2one(
        'product.product',
        'Deposit Product',
        domain="[('type', '=', 'service')]",
        help='Default product used for payment advances')
    auto_done_setting = fields.Selection([
        (0, "Allow to edit sales order from the 'Sales Order' menu (not from the Quotation menu)"),
        (1, "Never allow to modify a confirmed sale order")
        ], "Sale Order Modification")
    module_sale_contract = fields.Boolean("Manage subscriptions and recurring invoicing")
    module_website_sale_digital = fields.Boolean("Sell digital products - provide downloadable content on your customer portal")
    module_website_portal = fields.Boolean("Enable customer portal to track orders, delivery and invoices")
    module_sale_order_dates = fields.Selection([
        (0, 'Procurements and deliveries dates are based on the sale order dates'),
        (1, 'Allow to modify the sale order dates to postpone deliveries and procurements')
        ], "Date")

    @api.multi
    def set_sale_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'sale_pricelist_setting', self.sale_pricelist_setting)

    @api.multi
    def set_deposit_product_id_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'deposit_product_id_setting', self.deposit_product_id_setting.id)

    @api.multi
    def set_auto_done_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'auto_done_setting', self.auto_done_setting)

    @api.onchange('sale_pricelist_setting')
    def _onchange_sale_price(self):
        if self.sale_pricelist_setting == 'percentage':
            self.update({
                'group_product_pricelist': True,
                'group_sale_pricelist': True,
                'group_pricelist_item': False,
            })
        elif self.sale_pricelist_setting == 'formula':
            self.update({
                'group_product_pricelist': False,
                'group_sale_pricelist': True,
                'group_pricelist_item': True,
            })
        else:
            self.update({
                'group_product_pricelist': False,
                'group_sale_pricelist': False,
                'group_pricelist_item': False,
            })

    @api.multi
    def set_sale_tax_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'sale_show_tax', self.sale_show_tax)

    @api.onchange('sale_show_tax')
    def _onchange_sale_tax(self):
        if self.sale_show_tax == "subtotal":
            self.update({
                'group_show_price_total': False,
                'group_show_price_subtotal': True,
            })
        else:
            self.update({
                'group_show_price_total': True,
                'group_show_price_subtotal': False,
            })
