# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
import werkzeug.urls

from odoo import api, fields, models, tools


class MailMail(models.Model):
    """Add the mass mailing campaign data to mail"""
    _inherit = ['mail.mail']

    mailing_id = fields.Many2one('mailing.mailing', string='Mass Mailing')
    mailing_trace_ids = fields.One2many('mailing.trace', 'mail_mail_id', string='Statistics')

    def _get_tracking_url(self):
        token = self._generate_mail_recipient_token(self.id)
        # Build the tracking URL on the recipient's website, like the rendered body (multi-website setups).
        record = self.env[self.model].browse(self.res_id) if (self.mailing_id and self.model and self.res_id) else self
        return werkzeug.urls.url_join(
            record.get_base_url(),
            f'mail/track/{self.id}/{token}/blank.gif'
        )

    @api.model
    def _generate_mail_recipient_token(self, mail_id):
        return tools.hmac(self.env(su=True), 'mass_mailing-mail_mail-open', mail_id)

    def _prepare_outgoing_body(self):
        """ Override to add the tracking URL to the body and to add trace ID in
        shortened urls """
        self.ensure_one()
        # super() already cleans pseudo-void content from editor
        body = super()._prepare_outgoing_body()

        if body and self.mailing_id and self.mailing_trace_ids:
            Wrapper = body.__class__
            for match in set(re.findall(tools.mail.URL_REGEX, body)):
                href = match[0]
                url = match[1]

                parsed = werkzeug.urls.url_parse(url, scheme='http')

                if parsed.scheme.startswith('http') and parsed.path.startswith('/r/'):
                    new_href = href.replace(url, f"{url}/m/{self.mailing_trace_ids[0].id}")
                    body = body.replace(Wrapper(href), Wrapper(new_href))

            # generate tracking URL, unless tracking is disabled for this recipient
            disable_all, _country_codes = self.env['mailing.mailing']._get_tracking_disabled_config()
            if not disable_all and self.id not in self.env.context.get('mailing_untracked_mail_ids', ()):
                tracking_url = self._get_tracking_url()
                body = tools.mail.append_content_to_html(
                    body,
                    f'<img src="{tracking_url}"/>',
                    plaintext=False,
                )
        return body

    def _send(self, *args, **kwargs):
        """ Flag, in batch, mailing emails whose recipient country forbids
        tracking, so that '_prepare_outgoing_body' skips the opening pixel. """
        Mailing = self.env['mailing.mailing']
        additional_context = {}
        # disable_all is checked directly in '_prepare_outgoing_body'
        _disable_all, country_codes = Mailing._get_tracking_disabled_config()
        if country_codes:
            untracked_mail_ids = set()
            for model, model_mails in self.filtered(lambda m: m.mailing_id and m.model and m.res_id).grouped('model').items():
                untracked_res_ids = Mailing._get_untracked_res_ids(model, model_mails.mapped('res_id'))
                untracked_mail_ids.update(model_mails.filtered(lambda m: m.res_id in untracked_res_ids).ids)
            additional_context['mailing_untracked_mail_ids'] = frozenset(untracked_mail_ids)
        return super(MailMail, self.with_context(**additional_context))._send(*args, **kwargs)

    def _prepare_outgoing_list(self, mail_server=False, recipients_follower_status=None):
        """ Update mailing specific links to replace generic unsubscribe and
        view links by email-specific links. Also add headers to allow
        unsubscribe from email managers. """
        email_list = super()._prepare_outgoing_list(mail_server=mail_server,
                                                    recipients_follower_status=recipients_follower_status)
        if not self.res_id or not self.mailing_id:
            return email_list

        # The body was rendered with the recipient's base URL (per-website in multi-website
        # setups), so build the links on that same base URL for the substitutions below to match.
        recipient = self.env[self.model].browse(self.res_id) if self.model else self.mailing_id
        base_url = recipient.get_base_url()
        mailing = self.mailing_id.with_context(mailing_recipient_record=recipient)
        for email_values in email_list:
            if not email_values['email_to']:
                continue

            # prepare links with normalize email
            email_normalized = tools.email_normalize(email_values['email_to'][0], strict=False)
            email_to = email_normalized or email_values['email_to'][0]

            unsubscribe_url = mailing._get_unsubscribe_url(email_to, self.res_id)
            unsubscribe_oneclick_url = mailing._get_unsubscribe_oneclick_url(email_to, self.res_id)
            view_url = mailing._get_view_url(email_to, self.res_id)

            # replace links in body
            if not tools.is_html_empty(email_values['body']):
                # replace generic link by recipient-specific one, except if we know
                # by advance it won't work (i.e. testing mailing scenario)
                if f'{base_url}/unsubscribe_from_list' in email_values['body'] and not self.env.context.get('mailing_test_mail'):
                    email_values['body'] = email_values['body'].replace(
                        f'{base_url}/unsubscribe_from_list',
                        unsubscribe_url,
                    )
                if f'{base_url}/view' in email_values['body']:
                    email_values['body'] = email_values['body'].replace(
                        f'{base_url}/view',
                        view_url,
                    )

            # add headers
            email_values['headers'].update({
                'List-Unsubscribe': f'<{unsubscribe_oneclick_url}>',
                'List-Unsubscribe-Post': 'List-Unsubscribe=One-Click',
                'Precedence': 'list',
                'X-Auto-Response-Suppress': 'OOF',  # avoid out-of-office replies from MS Exchange
            })
        return email_list

    def _postprocess_sent_message(self, success_pids, failure_reason=False, failure_type=None):
        if failure_type:  # we consider that a recipient error is a failure with mass mailing and show them as failed
            self.filtered('mailing_id').mailing_trace_ids.set_failed(failure_type=failure_type)
        else:
            self.filtered('mailing_id').mailing_trace_ids.set_sent()
        return super()._postprocess_sent_message(success_pids, failure_reason=failure_reason, failure_type=failure_type)
