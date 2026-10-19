# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError

from odoo.addons.base.models.ir_qweb_fields import nl2br_enclose


class WithdrawalRequest(models.Model):
    _name = "withdrawal.request"
    _description = "Withdrawal Request"
    _rec_name = "order_reference"

    email = fields.Char(string="Your Email", required=True)
    order_reference = fields.Char(related="order_id.name", store=True, readonly=False)
    order_id = fields.Many2one(comodel_name="sale.order", string="Order", required=True, index=True)
    recipient_emails = fields.Char(string="Recipient Emails")
    log_message = fields.Text(string="Message")

    def website_form_input_filter(self, request, values):
        order_reference = values.get("order_reference")
        email = values.get("email")
        order = (
            order_reference and email and self._find_order_by_ref_and_email(order_reference, email)
        )
        if not order:
            raise UserError(
                self.env._(
                    "We could not find any order matching this email address and order number."
                )
            )
        values["order_id"] = order.id
        values.pop("order_reference", None)
        values["recipient_emails"] = request.params.get("recipient_emails")
        if form_fields := dict(request.params):
            fields_info = self.fields_get(form_fields.keys(), attributes=["string"])
            blacklisted_fields = self._blacklisted_fields()
            values["log_message"] = "\n".join([
                self.env._("Withdrawal Requested"),
                *(
                    f"{fields_info[name]['string'] if name in fields_info else name}: {value}"
                    for name, value in form_fields.items()
                    if value and isinstance(value, str) and name not in blacklisted_fields
                ),
            ])
        return values

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            if record.order_id:
                mail_content = record._send_confirmation_customer()
                record._notify_withdrawal_request()
                record._log_mail_sent_to_customer(mail_content)
                # Log the withdrawal request fields filled in by the customer in the order's chatter
                record.order_id._message_log(body=nl2br_enclose(record.log_message, "p"))
        return records

    @api.model
    def _find_order_by_ref_and_email(self, order_reference, email):
        """Return the order matching both the given reference and customer email."""
        return (
            self
            .env["sale.order"]
            .sudo()
            .search(
                [
                    ("name", "=ilike", order_reference),
                    ("partner_id.email", "=ilike", email),
                    ("state", "=", "sale"),
                ],
                limit=1,
            )
        )

    def _blacklisted_fields(self):
        """Return the list of fields that should not be displayed."""
        return [
            *models.MAGIC_COLUMNS,
            "display_name",
            "model_name",
            "context",
            "website_form_signature",
            "recipient_emails",
        ]

    def _send_confirmation_customer(self):
        """Send the withdrawal request confirmation email to the customer.

        :return: the subject and body of the message, to be logged on the
            withdrawal request's related records.
        :rtype: dict
        """
        self.ensure_one()
        order = self.order_id
        template = self.env.ref("website_sale.mail_template_sale_withdrawal_request_confirmation")
        # detach the email from the record, so that it is not logged in the chatter
        template.send_mail(
            order.id,
            force_send=True,
            email_values={
                "model": False,
                "res_id": False,
                "email_to": order.partner_id.email_formatted,
            },
        )
        rendered = template._generate_template(order.ids, ["subject", "body_html"])[order.id]
        return {"subject": rendered["subject"], "body": rendered["body_html"]}

    def _notify_withdrawal_request(self):
        """Notify the internal team that a withdrawal request was submitted."""
        self.ensure_one()
        if recipient_emails := self.recipient_emails:
            template = self.env.ref("website_sale.mail_template_withdrawal_request_notification")
            order_access_link = self.order_id._notify_get_action_link(
                "view", model="sale.order", res_id=self.order_id.id
            )
            template.with_context(order_access_link=order_access_link).send_mail(
                self.id,
                force_send=True,
                email_values={
                    "email_to": recipient_emails,
                    "email_from": self.env.company.email_formatted or self.env.user.email_formatted,
                },
            )

    def _log_mail_sent_to_customer(self, mail_content):
        """Log the confirmation message sent to the customer on the order's chatter."""
        self.ensure_one()
        self.order_id.message_post(
            subject=mail_content["subject"],
            body=mail_content["body"],
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
        )

    @api.autovacuum
    def _gc_withdrawal_requests(self):
        """Delete withdrawal requests older than 1 hour."""
        self.search([("create_date", "<=", fields.Datetime.now() - timedelta(hours=1))]).unlink()
