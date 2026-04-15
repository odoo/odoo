# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    is_donation = fields.Boolean(string="Is donation")
    donation_log_message = fields.Html(string="Donation Log Message")

    def _post_process(self):
        super()._post_process()
        for donation_tx in self.filtered(lambda tx: tx.state == 'done' and tx.is_donation):
            donation_tx._send_donation_email()
            # Log the donation message to the payment record's message history
            donation_tx.payment_id._message_log(body=donation_tx.donation_log_message)

    def _send_donation_email(self, is_internal_notification=False, comment=None, recipient_email=None):
        self.ensure_one()
        if is_internal_notification or self.state == 'done':
            if is_internal_notification:
                recipient_user = self.env['res.users'].search(
                    [('email', '=', recipient_email)], limit=1,
                )
                lang = recipient_user.lang or self.company_id.partner_id.lang
            else:
                lang = self.partner_lang
            env = self.with_context(lang=lang).env
            subject = (
                env._("A donation has been made on your website")
                if is_internal_notification
                else env._("Donation confirmation")
            )
            body = self.env['ir.qweb'].with_context(lang=lang)._render('website_payment.donation_mail_body', {
                'is_internal_notification': is_internal_notification,
                'tx': self,
                'comment': comment,
            }, minimal_qcontext=True)
            body = self.env['mail.render.mixin'].with_context(lang=lang)._render_encapsulate(
                'mail.mail_notification_light',
                body,
                context_record=self,
            )
            self.env['mail.mail'].sudo().create({
                'author_id': self.partner_id.id,
                'body_html': body,
                'email_from': self.company_id.email_formatted,
                'email_to': recipient_email if is_internal_notification else self.partner_email,
                'subject': subject,
            }).send()
