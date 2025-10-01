# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup

from odoo import _, fields, models
from lxml import etree


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    is_donation = fields.Boolean(string="Is donation")
    extra_fields = fields.Json(string="Extra fields")

    def _post_process(self):
        super()._post_process()
        view = self.env['ir.ui.view'].search([('name', '=', 'website_payment.payment_form')])
        field_names = ['company_id', 'partner_id', 'partner_name', 'partner_country_id', 'partner_email']
        if len(view) > 1:
            view = view[1]
            # Parse the QWeb HTML
            html_tree = etree.HTML(view.arch)
            # Find all elements with class 's_website_form_fields'
            form_fields = html_tree.xpath("//input[contains(@class, 's_website_form_input')] | //select[contains(@class, 's_website_form_input')] | //textarea[contains(@class, 's_website_form_input')]")
            # Extract the names of fields or any relevant attributes
            field_names += [field.get('name') for field in form_fields if field.get('name')]
            field_names = list(dict.fromkeys(field_names))

        for donation_tx in self.filtered(lambda tx: tx.state == 'done' and tx.is_donation):
            donation_tx._send_donation_email()
            msg = [_('Payment received from donation with following details:')]
            for field in field_names:
                match_key = f'partner_{field}' if f'partner_{field}' in donation_tx._fields else field
                if match_key in donation_tx._fields:
                    field_name = donation_tx._fields[match_key].string
                    value = donation_tx[match_key]
                    if value:
                        if hasattr(value, 'name'):
                            value = value.name
                        msg.append(Markup('<br/>- %s: %s') % (field_name, value))
                elif donation_tx.extra_fields and match_key in donation_tx.extra_fields:
                    value = donation_tx.extra_fields[match_key]
                    if value:
                        field_label = match_key.replace('_', ' ').title()
                        msg.append(Markup('<br/>- %s: %s') % (field_label, value))
            donation_tx.payment_id._message_log(body=Markup().join(msg))

    def _send_donation_email(self, is_internal_notification=False, comment=None, recipient_email=None):
        self.ensure_one()
        if is_internal_notification or self.state == 'done':
            subject = _('A donation has been made on your website') if is_internal_notification else _('Donation confirmation')
            body = self.env['ir.qweb'].with_context(lang=self.partner_id.lang)._render('website_payment.donation_mail_body', {
                'is_internal_notification': is_internal_notification,
                'tx': self,
                'comment': comment,
            }, minimal_qcontext=True)
            body = self.env['mail.render.mixin'].with_context(lang=self.partner_id.lang)._render_encapsulate(
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
