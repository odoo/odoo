# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class SaleConfiguration(models.TransientModel):
    _inherit = 'sale.config.settings'

    sale_note = fields.Text(related='company_id.sale_note', string="Terms & Conditions")
    default_use_sale_note = fields.Boolean(string='Default Terms & Conditions', default_model='sale.config.settings')
    group_product_variant = fields.Boolean("Attributes & Variants",
        implied_group='product.group_product_variant')
    group_sale_pricelist = fields.Boolean("Use pricelists to adapt your price per customers",
        implied_group='product.group_sale_pricelist',
        help="""Allows to manage different prices based on rules per category of customers.
                Example: 10% for retailers, promotion of 5 EUR on this product, etc.""")
    group_pricelist_item = fields.Boolean("Show pricelists to customers",
        implied_group='product.group_pricelist_item')
    group_product_pricelist = fields.Boolean("Show pricelists On Products",
        implied_group='product.group_product_pricelist')
    group_uom = fields.Boolean("Units of Measure",
        implied_group='product.group_uom')
    group_discount_per_so_line = fields.Boolean("Discounts", implied_group='sale.group_discount_per_so_line')
    group_stock_packaging = fields.Boolean("Packaging", implied_group='product.group_stock_packaging',
        help="""Ability to select a package type in sales orders and 
                to force a quantity that is a multiple of the number of units per package.""")
    module_sale_margin = fields.Boolean("Margins")
    group_sale_layout = fields.Boolean("Sections on Sales Orders", implied_group='sale.group_sale_layout')
    group_warning_sale = fields.Boolean("Warnings", implied_group='sale.group_warning_sale')
    module_website_quote = fields.Boolean("Online Quotations & Templates")
    group_sale_delivery_address = fields.Boolean("Customer Addresses", implied_group='sale.group_delivery_invoice_address')
    multi_sales_price = fields.Boolean("Multiple sales price per product", default_model='sale.config.settings')
    multi_sales_price_method = fields.Selection([
        ('percentage', 'Multiple prices per product (e.g. customer segments, currencies)'),
        ('formula', 'Price computed from formulas (discounts, margins, roundings)')
        ], string="Pricelists")
    sale_pricelist_setting = fields.Selection([
        ('fixed', 'A single sales price per product'),
        ('percentage', 'Multiple prices per product (e.g. customer segments, currencies)'),
        ('formula', 'Price computed from formulas (discounts, margins, roundings)')
        ], string="Pricelists")
    group_show_price_subtotal = fields.Boolean(
        "Show subtotal",
        implied_group='sale.group_show_price_subtotal',
        group='base.group_portal,base.group_user,base.group_public')
    group_show_price_total = fields.Boolean(
        "Show total",
        implied_group='sale.group_show_price_total',
        group='base.group_portal,base.group_user,base.group_public')
    sale_show_tax = fields.Selection([
        ('subtotal', 'Tax-Included Prices'),
        ('total', 'Tax-Excluded Prices')], "Tax Display",
        default='subtotal',
        required=True)
    default_invoice_policy = fields.Selection([
        ('order', 'Ordered quantities'),
        ('delivery', 'Delivered quantities or service hours')
        ], 'Invoicing Policy',
        default='order',
        default_model='product.template')
    deposit_product_id_setting = fields.Many2one(
        'product.product',
        'Deposit Product',
        domain="[('type', '=', 'service')]",
        help='Default product used for payment advances')
    auto_done_setting = fields.Boolean("Lock Confirmed Orders")
    module_sale_contract = fields.Boolean("Subscriptions")
    module_website_sale_digital = fields.Boolean("Sell digital products - provide downloadable content on your customer portal")

    group_multi_currency = fields.Boolean("Multi-Currencies", implied_group='base.group_multi_currency')
    module_sale_stock = fields.Boolean("Inventory Management")
    module_delivery = fields.Boolean("Shipping Costs")
    module_delivery_dhl = fields.Boolean("DHL")
    module_delivery_fedex = fields.Boolean("FedEx")
    module_delivery_ups = fields.Boolean("UPS")
    module_delivery_usps = fields.Boolean("USPS")

    module_timesheet_grid_sale = fields.Boolean("Timesheets")
    module_sale_ebay = fields.Boolean("eBay")
    module_print_docsaway = fields.Boolean("Docsaway")
    module_web_clearbit = fields.Boolean("Customer Autocomplete")
    module_product_email_template = fields.Boolean("Specific Email")
    module_sale_coupon = fields.Boolean("Coupons & Promotions")

    @api.model
    def get_default_sale_pricelist_setting(self, fields):
        sale_pricelist_setting = self.env['ir.values'].get_default('sales.config.settings', 'sale_pricelist_setting')
        multi_sales_price = sale_pricelist_setting in ['percentage', 'formula']
        return {
            'sale_pricelist_setting': sale_pricelist_setting,
            'multi_sales_price': multi_sales_price,
            'multi_sales_price_method': multi_sales_price and sale_pricelist_setting or False
        }

    @api.onchange('multi_sales_price', 'multi_sales_price_method')
    def _onchange_sale_price(self):
        self.sale_pricelist_setting = self.multi_sales_price and self.multi_sales_price_method or 'fixed'
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

    def set_default_sale_pricelist_setting(self):
        return self.env['ir.values'].sudo().set_default('sales.config.settings', 'sale_pricelist_setting', self.sale_pricelist_setting)

    def set_deposit_product_id_defaults(self):
        return self.env['ir.values'].sudo().set_default('sale.config.settings', 'deposit_product_id_setting', self.deposit_product_id_setting.id)

    def set_auto_done_defaults(self):
        return self.env['ir.values'].sudo().set_default('sale.config.settings', 'auto_done_setting', self.auto_done_setting)

    def set_sale_tax_defaults(self):
        return self.env['ir.values'].sudo().set_default('sale.config.settings', 'sale_show_tax', self.sale_show_tax)

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
