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

    @api.model_create_multi
    def create(self, values_list):
        """ Override mail_mail creation to create an entry in mail.mail.statistics """
        # TDE note: should be after 'all values computed', to have values (FIXME after merging other branch holding create refactoring)
        mails = super(MailMail, self).create(values_list)
        for mail, values in zip(mails, values_list):
            if values.get('mailing_trace_ids'):
                mail.mailing_trace_ids.write({'message_id': mail.message_id})
        return mails

    def _get_tracking_url(self):
        token = tools.hmac(self.env(su=True), 'mass_mailing-mail_mail-open', self.id)
        return werkzeug.urls.url_join(self.get_base_url(), 'mail/track/%s/%s/blank.gif' % (self.id, token))

    def _send_prepare_body(self):
        """ Override to add the tracking URL to the body and to add
        trace ID in shortened urls """
        self.ensure_one()
        body = super(MailMail, self)._send_prepare_body()

        if not tools.is_html_empty(body) and self.mailing_id and self.mailing_trace_ids:
            for match in set(re.findall(tools.URL_REGEX, body)):
                href = match[0]
                url = match[1]

                parsed = werkzeug.urls.url_parse(url, scheme='http')

                if parsed.scheme.startswith('http') and parsed.path.startswith('/r/'):
                    new_href = href.replace(url, url + '/m/' + str(self.mailing_trace_ids[0].id))
                    body = body.replace(href, new_href)

            # generate tracking URL
            tracking_url = self._get_tracking_url()
            body = tools.append_content_to_html(
                body,
                '<img src="%s"/>' % tracking_url,
                plaintext=False,
            )
        return body

    def _send_prepare_outgoing_list(self):
        email_list = super(MailMail, self)._send_prepare_outgoing_list()
        if self.mailing_id and self.res_id:
            base_url = self.mailing_id.get_base_url()
            for email_values in email_list:
                if not email_values['body'] or not email_values['email_to']:
                    continue
                emails = tools.email_split(email_values['email_to'][0])
                email_to = emails[0] if emails else False

                urls_to_replace = [
                    (base_url + '/unsubscribe_from_list', self.mailing_id._get_unsubscribe_url(email_to, self.res_id)),
                    (base_url + '/view', self.mailing_id._get_view_url(email_to, self.res_id))
                ]

                for url_to_replace, new_url in urls_to_replace:
                    if url_to_replace in email_values['body']:
                        email_values['body'] = email_values['body'].replace(url_to_replace, new_url if new_url else '#')
        return email_list

    def _postprocess_sent_message(self, success, success_pids,
                                  notifications=False,
                                  failure_reason=False, failure_type=None):
        mail_sent = not failure_type  # we consider that a recipient error is a failure with mass mailling and show them as failed
        for mail in self:
            if mail.mailing_id:
                if mail_sent is True and mail.mailing_trace_ids:
                    mail.mailing_trace_ids.set_sent()
                elif mail_sent is False and mail.mailing_trace_ids:
                    mail.mailing_trace_ids.set_failed(failure_type=failure_type)
        return super(MailMail, self)._postprocess_sent_message(
            success, success_pids,
            notifications=notifications,
            failure_reason=failure_reason, failure_type=failure_type
        )
