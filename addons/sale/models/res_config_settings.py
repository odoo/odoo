# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Defaults
    default_invoice_policy = fields.Selection([
        ('order', 'Invoice what is ordered'),
        ('delivery', 'Invoice what is delivered')
        ], 'Invoicing Policy',
        default='order',
        default_model='product.template')

    # Groups
    group_auto_done_setting = fields.Boolean(
        string="Lock Confirmed Sales", implied_group='sale.group_auto_done_setting')
    group_proforma_sales = fields.Boolean(
        string="Pro-Forma Invoice", implied_group='sale.group_proforma_sales',
        help="Allows you to send pro-forma invoice.")
    group_warning_sale = fields.Boolean("Sale Order Warnings", implied_group='sale.group_warning_sale')

    # Config params
    automatic_invoice = fields.Boolean(
        string="Automatic Invoice",
        help="The invoice is generated automatically and available in the customer portal when the "
             "transaction is confirmed by the payment provider.\nThe invoice is marked as paid and "
             "the payment is registered in the payment journal defined in the configuration of the "
             "payment provider.\nThis mode is advised if you issue the final invoice at the order "
             "and not after the delivery.",
        config_parameter='sale.automatic_invoice',
    )
    confirmation_mail_template_id = fields.Many2one(
        comodel_name='mail.template',
        string='Confirmation Email Template',
        domain="[('model', '=', 'sale.order')]",
        config_parameter='sale.default_confirmation_template',
        help="Email sent to the customer once the order is paid."
    )
    deposit_default_product_id = fields.Many2one(
        'product.product',
        'Deposit Product',
        domain="[('type', '=', 'service')]",
        config_parameter='sale.default_deposit_product_id',
        help='Default product used for payment advances')

    invoice_mail_template_id = fields.Many2one(
        comodel_name='mail.template',
        string='Invoice Email Template',
        domain="[('model', '=', 'account.move')]",
        config_parameter='sale.default_invoice_email_template',
        help="Email sent to the customer once the invoice is available.",
    )

    use_quotation_validity_days = fields.Boolean(
        "Default Quotation Validity", config_parameter='sale.use_quotation_validity_days')

    # Company setup
    quotation_validity_days = fields.Integer(
        related='company_id.quotation_validity_days', string="Default Quotation Validity (Days)", readonly=False)
    portal_confirmation_sign = fields.Boolean(
        related='company_id.portal_confirmation_sign', string='Online Signature', readonly=False)
    portal_confirmation_pay = fields.Boolean(
        related='company_id.portal_confirmation_pay', string='Online Payment', readonly=False)

    # Modules
    module_delivery = fields.Boolean("Delivery Methods")
    module_delivery_bpost = fields.Boolean("bpost Connector")
    module_delivery_dhl = fields.Boolean("DHL Express Connector")
    module_delivery_easypost = fields.Boolean("Easypost Connector")
    module_delivery_sendcloud = fields.Boolean("Sendcloud Connector")
    module_delivery_fedex = fields.Boolean("FedEx Connector")
    module_delivery_ups = fields.Boolean("UPS Connector")
    module_delivery_usps = fields.Boolean("USPS Connector")

    module_product_email_template = fields.Boolean("Specific Email")
    module_sale_amazon = fields.Boolean("Amazon Sync")
    module_sale_loyalty = fields.Boolean("Coupons & Loyalty")
    module_sale_margin = fields.Boolean("Margins")

    #=== ONCHANGE METHODS ===#

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

    #=== CRUD METHODS ===#

    def set_values(self):
        super().set_values()
        if self.default_invoice_policy != 'order':
            self.env['ir.config_parameter'].set_param('sale.automatic_invoice', False)

        send_invoice_cron = self.env.ref('sale.send_invoice_cron', raise_if_not_found=False)
        if send_invoice_cron and send_invoice_cron.active != self.automatic_invoice:
            send_invoice_cron.active = self.automatic_invoice
