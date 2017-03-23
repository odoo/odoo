# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields

class WebsiteConfigSettings(models.TransientModel):
    _inherit = 'website.config.settings'

    def _default_order_mail_template(self):
        if self.env['ir.module.module'].search([('name', '=', 'website_quote')]).state in ('installed', 'to upgrade'):
            return self.env.ref('website_quote.confirmation_mail').id
        else:
            return self.env.ref('sale.email_template_edi_sale').id

    salesperson_id = fields.Many2one('res.users', related='website_id.salesperson_id', string='Salesperson')
    salesteam_id = fields.Many2one('crm.team', related='website_id.salesteam_id', string='Sales Channel', domain=[('team_type', '!=', 'pos')])
    module_delivery = fields.Boolean("Manage shipping internally")
    module_website_sale_delivery = fields.Boolean("Shipping Costs")
    # field used to have a nice radio in form view, resuming the 2 fields above
    sale_delivery_settings = fields.Selection([
        ('none', 'No shipping management on website'),
        ('internal', "Delivery methods are only used internally: the customer doesn't pay for shipping costs"),
        ('website', "Delivery methods are selectable on the website: the customer pays for shipping costs"),
        ], string="Shipping Management")
    module_delivery_dhl = fields.Boolean("DHL integration")
    module_delivery_fedex = fields.Boolean("Fedex integration")
    module_delivery_ups = fields.Boolean("UPS integration")
    module_delivery_usps = fields.Boolean("USPS integration")

    module_sale_ebay = fields.Boolean("eBay connector")
    module_sale_coupon = fields.Boolean("Discount Programs")

    group_website_multiimage = fields.Boolean(string='Multi-Images', implied_group='website_sale.group_website_multi_image')
    group_discount_per_so_line = fields.Boolean(string="Discounted Prices", implied_group='sale.group_discount_per_so_line')
    group_delivery_invoice_address = fields.Boolean(string="Shipping Address", implied_group='sale.group_delivery_invoice_address')

    module_website_sale_options = fields.Boolean("Optional Products", help='Installs *e-Commerce Optional Products*')
    module_website_sale_digital = fields.Boolean("Digital Content")
    module_website_sale_wishlist = fields.Boolean("Wishlists ", help='Installs *e-Commerce Wishlist*')
    module_website_sale_comparison = fields.Boolean("Product Comparator", help='Installs *e-Commerce Comparator*')

    module_sale_stock = fields.Boolean("Delivery Orders")

    # the next 2 fields represent sale_pricelist_setting from sale.config.settings, they are split here for the form view, to improve usability
    sale_pricelist_setting_split_1 = fields.Boolean(default=0, string="Multiple Prices per Product")
    sale_pricelist_setting_split_2 = fields.Selection([
        (0, 'Multiple prices per product (e.g. customer segments, currencies)'),
        (1, 'Prices computed from formulas (discounts, margins, roundings)')
        ], default=0, string="Sales Price")
    group_sale_pricelist = fields.Boolean("Use pricelists to adapt your price per customers",
        implied_group='product.group_sale_pricelist')

    group_product_variant = fields.Boolean("Attributes and Variants", implied_group='product.group_product_variant')
    group_pricelist_item = fields.Boolean("Show pricelists to customers",
        implied_group='product.group_pricelist_item')
    group_product_pricelist = fields.Boolean("Show pricelists On Products",
        implied_group='product.group_product_pricelist')

    order_mail_template = fields.Many2one('mail.template', string='Order Confirmation Email',
        default=_default_order_mail_template, domain="[('model', '=', 'sale.order')]",
        help="Email sent to customer at the end of the checkout process")
    group_show_price_subtotal = fields.Boolean("Show subtotal", implied_group='sale.group_show_price_subtotal')
    group_show_price_total = fields.Boolean("Show total", implied_group='sale.group_show_price_total')

    default_invoice_policy = fields.Selection([
        ('order', 'Ordered quantities'),
        ('delivery', 'Delivered quantities or service hours')
        ], 'Invoicing Policy', default='order')

    group_multi_currency = fields.Boolean(string='Multi-Currencies', implied_group='base.group_multi_currency')

    sale_show_tax = fields.Selection([
        ('total', 'Tax-Included Prices'),
        ('subtotal', 'Tax-Excluded Prices')],
        "Product Prices", default='total')

    @api.model
    def get_default_sale_delivery_settings(self, fields):
        sale_delivery_settings = 'none'
        if self.env['ir.module.module'].search([('name', '=', 'delivery')], limit=1).state in ('installed', 'to install', 'to upgrade'):
            sale_delivery_settings = 'internal'
            if self.env['ir.module.module'].search([('name', '=', 'website_sale_delivery')], limit=1).state in ('installed', 'to install', 'to upgrade'):
                sale_delivery_settings = 'website'
        return {'sale_delivery_settings': sale_delivery_settings}

    @api.model
    def get_default_sale_pricelist_setting(self, fields):
        return {'sale_pricelist_setting_split_1': 0 if self.env['ir.values'].get_defaults_dict('sale.config.settings').get('sale_pricelist_setting', 'fixed') == 'fixed' else 1,
                'sale_pricelist_setting_split_2': 0 if self.env['ir.values'].get_defaults_dict('sale.config.settings').get('sale_pricelist_setting', 'fixed') != 'formula' else 1}

    @api.model
    def set_sale_pricelist_settings(self):
        sale_pricelist_setting = 'formula'
        if self.sale_pricelist_setting_split_1 == 0:
            sale_pricelist_setting = 'fixed'
        elif self.sale_pricelist_setting_split_2 == 0:
            sale_pricelist_setting = 'percentage'
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'sale_pricelist_setting', sale_pricelist_setting)

    @api.multi
    def set_sale_tax_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'website.config.settings', 'sale_show_tax', self.sale_show_tax)

    @api.onchange('sale_delivery_settings')
    def _onchange_sale_delivery_settings(self):
        if self.sale_delivery_settings == 'none':
            self.update({
                'module_delivery': False,
                'module_website_sale_delivery': False,
            })
        elif self.sale_delivery_settings == 'internal':
            self.update({
                'module_delivery': True,
                'module_website_sale_delivery': False,
            })
        else:
            self.update({
                'module_delivery': True,
                'module_website_sale_delivery': True,
            })

    @api.onchange('group_discount_per_so_line')
    def _onchange_group_discount_per_so_line(self):
        if self.group_discount_per_so_line:
            self.update({
                'sale_pricelist_setting_split_1': True,
            })

    @api.onchange('sale_pricelist_setting_split_1', 'sale_pricelist_setting_split_2')
    def _onchange_sale_pricelist_setting(self):
        if self.sale_pricelist_setting_split_1 == 0:
            self.update({
                'group_product_pricelist': False,
                'group_sale_pricelist': False,
                'group_pricelist_item': False,
            })
        else:
            if self.sale_pricelist_setting_split_2 == 0:
                self.update({
                    'group_product_pricelist': True,
                    'group_sale_pricelist': True,
                    'group_pricelist_item': False,
                })
            else:
                self.update({
                    'group_product_pricelist': False,
                    'group_sale_pricelist': True,
                    'group_pricelist_item': True,
                })

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
