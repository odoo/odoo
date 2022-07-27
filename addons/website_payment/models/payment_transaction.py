# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    is_donation = fields.Boolean(string="Is donation", help="Is the payment a donation")

    def _finalize_post_processing(self):
        super()._finalize_post_processing()
        for tx in self.filtered('is_donation'):
            tx._send_donation_email()
            msg = [_('Payment received from donation with following details:')]
            for field in ['company_id', 'partner_id', 'partner_name', 'partner_country_id', 'partner_email']:
                field_name = tx._fields[field].string
                value = tx[field]
                if value:
                    if hasattr(value, 'name'):
                        value = value.name
                    msg.append('<br/>- %s: %s' % (field_name, value))
            tx.payment_id._message_log(body=''.join(msg))

    def _send_donation_email(self, is_internal_notification=False, comment=None, recipient_email=None):
        self.ensure_one()
        if is_internal_notification or self.state == 'done':
            subject = _('A donation has been made on your website') if is_internal_notification else _('Donation confirmation')
            body = self.env.ref('website_payment.donation_mail_body')._render({
                'is_internal_notification': is_internal_notification,
                'tx': self,
                'comment': comment,
            }, engine='ir.qweb', minimal_qcontext=True)
            self.env.ref('website_payment.mail_template_donation').send_mail(
                self.id, notif_layout="mail.mail_notification_light",
                force_send=True,
                email_values={
                    'email_to': recipient_email if is_internal_notification else self.partner_email,
                    'email_from': self.company_id.email_formatted,
                    'author_id': self.partner_id.id,
                    'subject': subject,
                    'body_html': body,
                },
            )
