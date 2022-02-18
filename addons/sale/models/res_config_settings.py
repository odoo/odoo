# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    group_auto_done_setting = fields.Boolean("Lock Confirmed Sales", implied_group='sale.group_auto_done_setting')
    module_sale_margin = fields.Boolean("Margins")
    quotation_validity_days = fields.Integer(related='company_id.quotation_validity_days', string="Default Quotation Validity (Days)", readonly=False)
    use_quotation_validity_days = fields.Boolean("Default Quotation Validity", config_parameter='sale.use_quotation_validity_days')
    group_warning_sale = fields.Boolean("Sale Order Warnings", implied_group='sale.group_warning_sale')
    portal_confirmation_sign = fields.Boolean(related='company_id.portal_confirmation_sign', string='Online Signature', readonly=False)
    portal_confirmation_pay = fields.Boolean(related='company_id.portal_confirmation_pay', string='Online Payment', readonly=False)
    group_proforma_sales = fields.Boolean(string="Pro-Forma Invoice", implied_group='sale.group_proforma_sales',
        help="Allows you to send pro-forma invoice.")
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
        help='Default product used for payment advances')

    module_delivery = fields.Boolean("Delivery Methods")
    module_delivery_dhl = fields.Boolean("DHL Express Connector")
    module_delivery_fedex = fields.Boolean("FedEx Connector")
    module_delivery_ups = fields.Boolean("UPS Connector")
    module_delivery_usps = fields.Boolean("USPS Connector")
    module_delivery_bpost = fields.Boolean("bpost Connector")
    module_delivery_easypost = fields.Boolean("Easypost Connector")

    module_product_email_template = fields.Boolean("Specific Email")
    module_sale_coupon = fields.Boolean("Coupons & Promotions")
    module_sale_amazon = fields.Boolean("Amazon Sync")

    automatic_invoice = fields.Boolean(related="company_id.automatic_invoice", readonly=False)
    invoice_mail_template_id = fields.Many2one(related="company_id.invoice_mail_template_id", readonly=False)
    confirmation_mail_template_id = fields.Many2one(related="company_id.confirmation_mail_template_id", readonly=False)

    def set_values(self):
        super().set_values()
        if self.default_invoice_policy != "order":
            self.automatic_invoice = False

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
