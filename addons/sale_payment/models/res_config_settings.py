# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    automatic_invoice = fields.Boolean("Automatic Invoice",
                                       help="The invoice is generated automatically and available in the customer portal "
                                            "when the transaction is confirmed by the payment acquirer.\n"
                                            "The invoice is marked as paid and the payment is registered in the payment journal "
                                            "defined in the configuration of the payment acquirer.\n"
                                            "This mode is advised if you issue the final invoice at the order and not after the delivery.",
                                       config_parameter='sale_payment.automatic_invoice')
    template_id = fields.Many2one('mail.template', 'Email Template',
                                  domain="[('model', '=', 'account.invoice')]",
                                  config_parameter='sale_payment.default_email_template',
                                  default=lambda self: self.env.ref('account.email_template_edi_invoice', False))
