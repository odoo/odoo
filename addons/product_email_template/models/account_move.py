# -*- coding: utf-8 -*-

from odoo import api, models, SUPERUSER_ID


class AccountMove(models.Model):
    _inherit = 'account.move'

    def invoice_validate_send_email(self):
        if self.env.su:
            # sending mail in sudo was meant for it being sent from superuser
            self = self.with_user(SUPERUSER_ID)
        for invoice in self.filtered(lambda x: x.move_type == 'out_invoice'):
            # send template only on customer invoice
            # subscribe the partner to the invoice
            if invoice.partner_id not in invoice.message_partner_ids:
                invoice.message_subscribe([invoice.partner_id.id])
            for line in invoice.invoice_line_ids:
                if line.product_id.email_template_id:
                    invoice.message_post_with_template(
                        line.product_id.email_template_id.id,
                        composition_mode="comment",
                        email_layout_xmlid="mail.mail_notification_light"
                    )
        return True

    def _post(self, soft=True):
        # OVERRIDE
        posted = super()._post(soft)
        posted.invoice_validate_send_email()
        return posted
