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
    salesteam_id = fields.Many2one('crm.team', related='website_id.salesteam_id', string='Sales Team')
    module_delivery = fields.Boolean("Manage shipping internally")
    module_website_sale_delivery = fields.Boolean("Add Delivery Costs to Online Sales")
    # field used to have a nice radio in form view, resuming the 2 fields above
    sale_delivery_settings = fields.Selection([
        ('none', 'No shipping management on website'),
        ('internal', "Delivery methods are only used internally: the customer doesn't pay for shipping costs"),
        ('website', "Delivery methods are selectable on the website: the customer pays for shipping costs"),
        ], string="Shipping Management")
    module_delivery_dhl = fields.Boolean("DHL integration")
    module_delivery_fedex = fields.Boolean("Fedex integration")
    module_delivery_temando = fields.Boolean("Temando integration")
    module_delivery_ups = fields.Boolean("UPS integration")
    module_delivery_usps = fields.Boolean("USPS integration")
    module_sale_ebay = fields.Boolean("eBay connector")
    group_website_multiimage = fields.Selection([
        (0, 'One image per product'),
        (1, 'Several images per product')
        ], string='Multi Images', implied_group='website_sale.group_website_multi_image', group='base.group_portal,base.group_user,base.group_public')
    module_website_sale_options = fields.Selection([
        (0, 'One-step "add to cart"'),
        (1, 'Suggest optional products when adding to cart (e.g. for a computer: warranty, software, etc.)')
        ], "Optional Products", help='Installs *e-Commerce Optional Products*')
    module_portal = fields.Boolean("Activate the customer portal", help="""Give your customers access to their documents.""")
    # the next 2 fields represent sale_pricelist_setting from sale.config.settings, they are split here for the form view, to improve usability
    sale_pricelist_setting_split_1 = fields.Selection([
        (0, 'A single sales price per product'),
        (1, 'Several prices selectable through a drop-down list or applied automatically via Geo-IP'),
        ], default=0, string="Pricing Strategy")
    sale_pricelist_setting_split_2 = fields.Selection([
        (0, 'Specific prices per customer segment, currency, etc.'),
        (1, 'Advanced pricing based on formulas (discounts, margins, rounding)')
        ], default=0, string="Sales Price",
        help='Specific prices per customer segment, currency, etc.: new pricing table available in product detail form (Sales tab).\n'
             'Advanced pricing based on formulas (discounts, margins, rounding): apply price rules from a new *Pricelists* menu in Configuration.')
    group_sale_pricelist = fields.Boolean("Use pricelists to adapt your price per customers",
        implied_group='product.group_sale_pricelist',
        help="""Allows to manage different prices based on rules per category of customers.
                Example: 10% for retailers, promotion of 5 EUR on this product, etc.""")
    group_pricelist_item = fields.Boolean("Show pricelists to customers",
        implied_group='product.group_pricelist_item')
    group_product_pricelist = fields.Boolean("Show pricelists On Products",
        implied_group='product.group_product_pricelist')
    order_mail_template = fields.Many2one('mail.template', string='Order Confirmation Email', readonly=True, default=_default_order_mail_template, help="Email sent to customer at the end of the checkout process")

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
