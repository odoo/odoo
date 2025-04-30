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
            comment_subtype_id = self.env['ir.model.data']._xmlid_to_res_id('mail.mt_comment')
            for line in invoice.invoice_line_ids:
                if line.product_id.email_template_id:
                    invoice.message_post_with_source(
                        line.product_id.email_template_id,
                        email_layout_xmlid="mail.mail_notification_light",
                        subtype_id=comment_subtype_id,
                    )
        return True

    def _post(self, soft=True):
        # OVERRIDE
        posted = super()._post(soft)
        posted.invoice_validate_send_email()
        return posted
