# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ast import literal_eval

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    sale_note = fields.Text(related='company_id.sale_note', string="Terms & Conditions")
    use_sale_note = fields.Boolean(
        string='Default Terms & Conditions',
        oldname='default_use_sale_note')
    group_discount_per_so_line = fields.Boolean("Discounts", implied_group='sale.group_discount_per_so_line')
    module_sale_margin = fields.Boolean("Margins")
    group_sale_layout = fields.Boolean("Sections on Sales Orders", implied_group='sale.group_sale_layout')
    group_warning_sale = fields.Boolean("Warnings", implied_group='sale.group_warning_sale')
    portal_confirmation = fields.Boolean('Online Signature & Payment')
    portal_confirmation_options = fields.Selection([
        ('sign', 'Signature'),
        ('pay', 'Payment')], string="Online Signature & Payment options")
    module_sale_payment = fields.Boolean("Online Signature & Payment", help='Technical field implied by user choice of online_confirmation')
    module_website_quote = fields.Boolean("Quotations Templates")
    group_sale_delivery_address = fields.Boolean("Customer Addresses", implied_group='sale.group_delivery_invoice_address')
    multi_sales_price = fields.Boolean("Multiple Sales Prices per Product")
    multi_sales_price_method = fields.Selection([
        ('percentage', 'Multiple prices per product (e.g. customer segments, currencies)'),
        ('formula', 'Prices computed from formulas (discounts, margins, roundings)')
        ], default='percentage', string="Pricelists")
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
    group_proforma_sales = fields.Boolean(string="Pro-Forma Invoice", implied_group='sale.group_proforma_sales',
        help="Allows you to send pro-forma invoice.")
    sale_show_tax = fields.Selection([
        ('subtotal', 'Tax-Excluded Prices'),
        ('total', 'Tax-Included Prices')], string="Tax Display",
        default='subtotal', required=True)
    default_invoice_policy = fields.Selection([
        ('order', 'Invoice what is ordered'),
        ('delivery', 'Invoice what is delivered')
        ], 'Invoicing Policy',
        default='order',
        default_model='product.template')
    default_deposit_product_id = fields.Many2one(
        'product.product',
        'Deposit Product',
        domain="[('type', '=', 'service')]",
        oldname='deposit_product_id_setting',
        help='Default product used for payment advances')
    auto_done_setting = fields.Boolean("Lock Confirmed Orders")
    module_website_sale_digital = fields.Boolean("Sell digital products - provide downloadable content on your customer portal")

    auth_signup_uninvited = fields.Selection([
        ('b2b', 'On invitation (B2B)'),
        ('b2c', 'Free sign up (B2C)'),
    ], string='Customer Account')

    module_delivery = fields.Boolean("Shipping Costs")
    module_delivery_dhl = fields.Boolean("DHL")
    module_delivery_fedex = fields.Boolean("FedEx")
    module_delivery_ups = fields.Boolean("UPS")
    module_delivery_usps = fields.Boolean("USPS")
    module_delivery_bpost = fields.Boolean("bpost")

    module_product_email_template = fields.Boolean("Specific Email")
    module_sale_coupon = fields.Boolean("Coupons & Promotions")

    @api.onchange('multi_sales_price', 'multi_sales_price_method')
    def _onchange_sale_price(self):
        if self.multi_sales_price and not self.multi_sales_price_method:
            self.update({
                'multi_sales_price_method': 'percentage',
            })
        self.sale_pricelist_setting = self.multi_sales_price and self.multi_sales_price_method or 'fixed'

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

    @api.onchange('sale_pricelist_setting')
    def _onchange_sale_pricelist_setting(self):
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

    @api.onchange('portal_confirmation')
    def _onchange_portal_confirmation(self):
        if not self.portal_confirmation:
            self.portal_confirmation_options = False
        elif not self.portal_confirmation_options:
            self.portal_confirmation_options = 'sign'

    @api.onchange('portal_confirmation_options')
    def _onchange_portal_confirmation_options(self):
        if self.portal_confirmation_options == 'pay':
            self.module_sale_payment = True

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        ICPSudo = self.env['ir.config_parameter'].sudo()
        sale_pricelist_setting = ICPSudo.get_param('sale.sale_pricelist_setting')
        sale_portal_confirmation_options = ICPSudo.get_param('sale.sale_portal_confirmation_options', default='none')
        default_deposit_product_id = literal_eval(ICPSudo.get_param('sale.default_deposit_product_id', default='False'))
        if default_deposit_product_id and not self.env['product.product'].browse(default_deposit_product_id).exists():
            default_deposit_product_id = False
        res.update(
            auth_signup_uninvited='b2c' if ICPSudo.get_param('auth_signup.allow_uninvited', 'False').lower() == 'true' else 'b2b',
            use_sale_note=ICPSudo.get_param('sale.use_sale_note', default=False),
            auto_done_setting=ICPSudo.get_param('sale.auto_done_setting'),
            default_deposit_product_id=default_deposit_product_id,
            sale_show_tax=ICPSudo.get_param('sale.sale_show_tax', default='subtotal'),
            multi_sales_price=sale_pricelist_setting in ['percentage', 'formula'],
            multi_sales_price_method=sale_pricelist_setting in ['percentage', 'formula'] and sale_pricelist_setting or False,
            sale_pricelist_setting=sale_pricelist_setting,
            portal_confirmation=sale_portal_confirmation_options in ('pay', 'sign'),
            portal_confirmation_options=sale_portal_confirmation_options if sale_portal_confirmation_options in ('pay', 'sign') else False,
        )
        return res

    @api.multi
    def set_values(self):
        super(ResConfigSettings, self).set_values()
        ICPSudo = self.env['ir.config_parameter'].sudo()
        ICPSudo.set_param('auth_signup.allow_uninvited', repr(self.auth_signup_uninvited == 'b2c'))
        ICPSudo.set_param("sale.use_sale_note", self.use_sale_note)
        ICPSudo.set_param("sale.auto_done_setting", self.auto_done_setting)
        ICPSudo.set_param("sale.default_deposit_product_id", self.default_deposit_product_id.id)
        ICPSudo.set_param('sale.sale_pricelist_setting', self.sale_pricelist_setting)
        ICPSudo.set_param('sale.sale_show_tax', self.sale_show_tax)
        ICPSudo.set_param('sale.sale_portal_confirmation_options', self.portal_confirmation_options if self.portal_confirmation_options in ('pay', 'sign') else 'none')
