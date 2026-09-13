from datetime import UTC, datetime
from urllib.parse import urlsplit

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, tools


class MailMail(models.Model):
    """Add the mass mailing campaign data to mail"""

    _inherit = "mail.mail"

    mailing_id = fields.Many2one(
        comodel_name="mailing.mailing",
        string="Mass Mailing",
    )
    mailing_trace_ids = fields.One2many(
        comodel_name="mailing.trace",
        inverse_name="mail_mail_id",
        string="Statistics",
    )

    def _get_tracking_url(self):
        token = self._generate_mail_recipient_token(self.id)
        return tools.urls.urljoin(
            self.get_base_url(), f"mail/track/{self.id}/{token}/blank.gif"
        )

    @api.model
    def _generate_mail_recipient_token(self, mail_id):
        return tools.hmac(self.env(su=True), "mass_mailing-mail_mail-open", mail_id)

    def _prepare_outgoing_body(self):
        """Override to add the tracking URL to the body and to add trace ID in
        shortened urls"""
        self.check_singleton()
        # super() already cleans pseudo-void content from editor
        body = super()._prepare_outgoing_body()

        if body and self.mailing_id and self.mailing_trace_ids:
            Wrapper = body.__class__
            for match in set(tools.mail.URL_REGEX.findall(body)):
                href = match[0]
                url = match[1]

                parsed = urlsplit(url, scheme="http")

                if parsed.scheme.startswith("http") and parsed.path.startswith("/r/"):
                    new_href = href.replace(
                        url, f"{url}/m/{self.mailing_trace_ids[0].id}"
                    )
                    body = body.replace(Wrapper(href), Wrapper(new_href))

            # generate tracking URL
            tracking_url = self._get_tracking_url()
            body = tools.mail.add_html_content(
                body,
                f'<img src="{tracking_url}"/>',
                plaintext=False,
            )
        return body

    def _prepare_outgoing_list(
        self,
        mail_server=False,
        doc_to_followers=None,
        smtp_session=None,
        already_sent_pids=None,
    ):
        """Update mailing specific links to replace generic unsubscribe and
        view links by email-specific links. Also add headers to allow
        unsubscribe from email managers.

        Each entry owns its ``headers`` dict, so the per-recipient values written
        below reach only the recipient they were computed for.
        """
        email_list = super()._prepare_outgoing_list(
            mail_server=mail_server,
            doc_to_followers=doc_to_followers,
            smtp_session=smtp_session,
            already_sent_pids=already_sent_pids,
        )
        if not self.res_id or not self.mailing_id:
            return email_list

        base_url = self.mailing_id.get_base_url()
        for email_values in email_list:
            if not email_values["email_to"]:
                continue

            # prepare links with normalize email
            email_normalized = tools.email_normalize(
                email_values["email_to"][0], strict=False
            )
            email_to = email_normalized or email_values["email_to"][0]

            unsubscribe_url = self.mailing_id._get_unsubscribe_url(
                email_to, self.res_id
            )
            unsubscribe_oneclick_url = self.mailing_id._get_unsubscribe_oneclick_url(
                email_to, self.res_id
            )
            view_url = self.mailing_id._get_view_url(email_to, self.res_id)

            # replace links in body
            if not tools.is_html_empty(email_values["body"]):
                # replace generic link by recipient-specific one, except if we know
                # by advance it won't work (i.e. testing mailing scenario)
                if f"{base_url}/unsubscribe_from_list" in email_values[
                    "body"
                ] and not self.env.context.get("mailing_test_mail"):
                    email_values["body"] = email_values["body"].replace(
                        f"{base_url}/unsubscribe_from_list",
                        unsubscribe_url,
                    )
                if f"{base_url}/view" in email_values["body"]:
                    email_values["body"] = email_values["body"].replace(
                        f"{base_url}/view",
                        view_url,
                    )

            # add headers
            email_values["headers"].update(
                {
                    "List-Unsubscribe": f"<{unsubscribe_oneclick_url}>",
                    "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
                    "Precedence": "list",
                    "X-Auto-Response-Suppress": "OOF",  # avoid out-of-office replies from MS Exchange
                }
            )
        return email_list

    def _postprocess_sent_message(
        self,
        success_partners,
        success_emails,
        failure_reason=False,
        failure_type=None,
        **kwargs,
    ):
        if failure_type:  # we consider that a recipient error is a failure with mass mailing and show them as failed
            self.filtered("mailing_id").mailing_trace_ids.set_failed(
                failure_type=failure_type
            )
        else:
            self.filtered("mailing_id").mailing_trace_ids.set_sent()
        super()._postprocess_sent_message(
            success_partners,
            success_emails,
            failure_reason=failure_reason,
            failure_type=failure_type,
            **kwargs,
        )

    _GC_CANCELED_BATCH_SIZE = 10000

    @api.autovacuum
    def _gc_canceled_mail_mail(self):
        """Garbage collects old canceled mail.mail records as we consider
        nobody is going to look at them anymore, becoming noise."""
        # _get_int_param, not get_param: the latter answers with the stored *string*
        # as soon as the parameter is set, and '6' <= 0 raises TypeError -- taking the
        # whole autovacuum down with it.
        months_limit = self.env["ir.config_parameter"]._get_int_param(
            "mass_mailing.cancelled_mails_months_limit", 6
        )
        if months_limit <= 0:
            return 0, False
        history_deadline = datetime.now(UTC) - relativedelta(
            months=months_limit
        )  # 6 months history will be kept
        canceled_mails = self.with_context(active_test=False).search(
            [("state", "=", "cancel"), ("write_date", "<=", history_deadline)],
            order="id asc",
            limit=self._GC_CANCELED_BATCH_SIZE,
        )

        canceled_mails.with_context(prefetch_fields=False).mail_message_id.unlink()
        return len(canceled_mails), len(canceled_mails) == self._GC_CANCELED_BATCH_SIZE
