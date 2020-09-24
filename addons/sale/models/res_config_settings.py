# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    sale_note = fields.Text(related='company_id.sale_note', string="Terms & Conditions", readonly=False)
    use_sale_note = fields.Boolean(
        string='Default Terms & Conditions',
        oldname='default_use_sale_note',
        config_parameter='sale.use_sale_note')
    group_discount_per_so_line = fields.Boolean("Discounts", implied_group='sale.group_discount_per_so_line')
    module_sale_margin = fields.Boolean("Margins")
    quotation_validity_days = fields.Integer(related='company_id.quotation_validity_days', string="Default Quotation Validity (Days)", readonly=False)
    use_quotation_validity_days = fields.Boolean("Default Quotation Validity", config_parameter='sale.use_quotation_validity_days')
    group_warning_sale = fields.Boolean("Sale Order Warnings", implied_group='sale.group_warning_sale')
    portal_confirmation_sign = fields.Boolean(related='company_id.portal_confirmation_sign', string='Online Signature', readonly=False)
    portal_confirmation_pay = fields.Boolean(related='company_id.portal_confirmation_pay', string='Online Payment', readonly=False)
    group_sale_delivery_address = fields.Boolean("Customer Addresses", implied_group='sale.group_delivery_invoice_address')
    multi_sales_price = fields.Boolean("Multiple Sales Prices per Product")
    multi_sales_price_method = fields.Selection([
        ('percentage', 'Multiple prices per product (e.g. customer segments, currencies)'),
        ('formula', 'Prices computed from formulas (discounts, margins, roundings)')
        ], default='percentage', string="Pricelists Method")
    sale_pricelist_setting = fields.Selection([
        ('fixed', 'A single sales price per product'),
        ('percentage', 'Multiple prices per product (e.g. customer segments, currencies)'),
        ('formula', 'Price computed from formulas (discounts, margins, roundings)')
        ], string="Pricelists", config_parameter='sale.sale_pricelist_setting')
    group_proforma_sales = fields.Boolean(string="Pro-Forma Invoice", implied_group='sale.group_proforma_sales',
        help="Allows you to send pro-forma invoice.")
    group_sale_order_dates = fields.Boolean("Delivery Date", implied_group='sale.group_sale_order_dates')
    default_invoice_policy = fields.Selection([
        ('order', 'Invoice what is ordered'),
        ('delivery', 'Invoice what is delivered')
        ], 'Invoicing Policy',
        default='order',
        default_model='product.template')
    deposit_default_product_id = fields.Many2one(
        'product.product',
        'Deposit Product',
        domain="[('type', '=', 'service')]",
        config_parameter='sale.default_deposit_product_id',
        oldname='default_deposit_product_id',
        help='Default product used for payment advances')
    auto_done_setting = fields.Boolean("Lock Confirmed Sales", config_parameter='sale.auto_done_setting')
    module_website_sale_digital = fields.Boolean("Digital Content")

    auth_signup_uninvited = fields.Selection([
        ('b2b', 'On invitation'),
        ('b2c', 'Free sign up'),
    ], string='Customer Account', default='b2b', config_parameter='auth_signup.invitation_scope')

    module_delivery = fields.Boolean("Shipping Costs")
    module_delivery_dhl = fields.Boolean("DHL Connector")
    module_delivery_fedex = fields.Boolean("FedEx Connector")
    module_delivery_ups = fields.Boolean("UPS Connector")
    module_delivery_usps = fields.Boolean("USPS Connector")
    module_delivery_bpost = fields.Boolean("bpost Connector")
    module_delivery_easypost = fields.Boolean("Easypost Connector")

    module_product_email_template = fields.Boolean("Specific Email")
    module_sale_coupon = fields.Boolean("Coupons & Promotions")

    automatic_invoice = fields.Boolean("Automatic Invoice",
                                       help="The invoice is generated automatically and available in the customer portal "
                                            "when the transaction is confirmed by the payment acquirer.\n"
                                            "The invoice is marked as paid and the payment is registered in the payment journal "
                                            "defined in the configuration of the payment acquirer.\n"
                                            "This mode is advised if you issue the final invoice at the order and not after the delivery.",
                                       config_parameter='sale.automatic_invoice')
    template_id = fields.Many2one('mail.template', 'Email Template',
                                  domain="[('model', '=', 'account.invoice')]",
                                  config_parameter='sale.default_email_template',
                                  default=lambda self: self.env.ref('account.email_template_edi_invoice', False))

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        if self.default_invoice_policy != 'order':
            self.env['ir.config_parameter'].set_param('sale.automatic_invoice', False)
        if not self.group_discount_per_so_line:
            pl = self.env['product.pricelist'].search([('discount_policy', '=', 'without_discount')])
            pl.write({'discount_policy': 'with_discount'})

    @api.onchange('multi_sales_price', 'multi_sales_price_method')
    def _onchange_sale_price(self):
        if self.multi_sales_price and not self.multi_sales_price_method:
            self.update({
                'multi_sales_price_method': 'percentage',
            })
        self.sale_pricelist_setting = self.multi_sales_price and self.multi_sales_price_method or 'fixed'

    @api.onchange('sale_pricelist_setting')
    def _onchange_sale_pricelist_setting(self):
        self.pos_pricelist_setting_sync(self.sale_pricelist_setting)
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

    def sale_pricelist_setting_sync(self, pos_pricelist_setting):
        if not pos_pricelist_setting:
            self.multi_sales_price = False
            self.sale_pricelist_setting = 'fixed'
        else:
            self.multi_sales_price = True
            self.sale_pricelist_setting = pos_pricelist_setting

    @api.onchange('portal_confirmation_pay')
    def _onchange_portal_confirmation_pay(self):
        if self.portal_confirmation_pay:
            self.module_sale_payment = True

    @api.onchange('use_quotation_validity_days')
    def _onchange_use_quotation_validity_days(self):
        if self.quotation_validity_days <= 0:
            self.quotation_validity_days = self.env['res.company'].default_get(['quotation_validity_days'])['quotation_validity_days']

    @api.onchange('quotation_validity_days')
    def _onchange_quotation_validity_days(self):
        if self.quotation_validity_days <= 0:
            self.quotation_validity_days = self.env['res.company'].default_get(['quotation_validity_days'])['quotation_validity_days']
            return {
                'warning': {'title': "Warning", 'message': "Quotation Validity is required and must be greater than 0."},
            }

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        ICPSudo = self.env['ir.config_parameter'].sudo()
        sale_pricelist_setting = ICPSudo.get_param('sale.sale_pricelist_setting')
        res.update(
            multi_sales_price=sale_pricelist_setting in ['percentage', 'formula'],
            multi_sales_price_method=sale_pricelist_setting in ['percentage', 'formula'] and sale_pricelist_setting or False,
            sale_pricelist_setting=sale_pricelist_setting,
        )
        return res
