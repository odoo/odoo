# -*- coding: utf-8 -*-

from odoo import api, models


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    def invoice_validate_send_email(self):
        for invoice in self.filtered(lambda x: x.type == 'out_invoice'):
            # send template only on customer invoice
            # subscribe the partner to the invoice
            if invoice.partner_id not in invoice.message_partner_ids:
                invoice.message_subscribe([invoice.partner_id.id])
            for line in invoice.invoice_line_ids:
                if line.product_id.email_template_id:
                    invoice.message_post_with_template(line.product_id.email_template_id.id, composition_mode='comment', custom_layout='mail.mail_notification_light')
        return True

    @api.multi
    def invoice_validate(self):
        res = super(AccountInvoice, self).invoice_validate()
        self.invoice_validate_send_email()
        return res
