# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class IrConfigParameter(models.Model):
    # Override of config parameter to specifically handle the template
    # rendering group (de)activation through ICP.

    # While being there, let us document quickly mail ICP.

    # Emailing
    # * 'mail.mail.queue.batch.size': used in MailMail.process_email_queue()
    #   to limit maximum number of mail.mail managed by each cron call to VALUE.
    #   1000 by default;
    # * 'mail.session.batch.size': used in MailMail._split_by_mail_configuration()
    #   to prepare batches of maximum VALUE mails to give at '_send()' at each
    #   iteration. For each iteration an SMTP server is opened and closed. It
    #   prepares data for 'send' in conjunction with auto_commit=True in order
    #   to avoid repeating batches in case of failure). 1000 by default;
    # * 'mail.mail.force.send.limit': used in
    #   - MailThread._notify_thread_by_email(): notification emails flow
    #   - MailComposer._action_send_mail_mass_mail(): mail composer in mass mail mode
    #   to force the cron queue usage and avoid sending too much emails in a given
    #   transaction. When 0 is set flows based on it are always using the email
    #   queue, no direct send is performed. Default value is 100;
    # * 'mail.batch_size': used in
    #   - MailComposer._action_send_mail_mass_mail(): mails generation based on records
    #   - MailThread._notify_thread_by_email(): mails generation for notification emails
    #   - MailTemplate.send_mail_batch(): mails generation done directly from templates
    #   to split mail generation in batches;
    #   - EventMail._execute_attendee_based() and EventMail._execute_event_based():
    #    mails (+ sms, whatsapp) generation for each attendee of en event;
    #    50 by default;
    # * 'mail.render.cron.limit': used in cron involving rendering of content
    #   and/or templates, like event mail scheduler cron. Defaults to 1000;

    # Mail Gateway
    #   * 'mail.gateway.loop.minutes' and 'mail.gateway.loop.threshold': block
    #     emails with same email_from if gateway received more than THRESHOLD
    #     in MINUTES. This is used to break loops e.g. when email servers bounce
    #     each other. 20 emails / 120 minutes by default;
    #   * 'mail.default.from_filter': default from_filter used when there is
    #     no specific outgoing mail server used to send emails;
    #   * 'mail.catchall.domain.allowed': optional list of email domains that
    #     restricts right-part of aliases when used in pre-17 compatibility
    #     mode (see MailAlias.alias_incoming_local);

    # Activities
    #   * 'mail.activity.gc.delete_overdue_years': if set, activities outdated
    #     for more than VALUE years are gc. 0 (skipped) by default;
    #   * 'mail.activity.systray.limit': number of activities fetched by the
    #     systray, to avoid performance issues notably with technical users that
    #     rarely connect. 1000 by default;

    # Groups
    #   * 'mail.restrict.template.rendering': ICP used in config settings to
    #     add or remove 'mail.group_mail_template_editor' group to internal
    #     users i.e. restrict or not QWeb rendering and edition by default.
    #     Not activated by default;

    # Discuss
    #   * 'mail.link_preview_throttle': avoid storing link previews for discuss
    #     if more than VALUE existing link previews are stored for the given
    #     domain in the last 10 seconds. 99 by default;
    #   * 'mail.chat_from_token': allow chat from token;

    # Configuration keys
    #   * 'mail.google_translate_api_key': key used to fetch translations using
    #     google translate;
    #   * 'mail.web_push_vapid_private_key' and 'mail.web_push_vapid_public_key':
    #     configuration parameters when using web push notifications;
    #   * 'mail.use_twilio_rtc_servers', 'mail.sfu_server_url' and 'mail.
    #     sfu_server_key': rtc server usage and configuration;
    #   * 'discuss.tenor_api_key', 'discuss.tenor_gif_limit' and 'discuss.
    #     tenor_content_filter' used for gif fetch service;
    _inherit = 'ir.config_parameter'

    @api.model
    def set_param(self, key, value):
        if key == 'mail.restrict.template.rendering':
            group_user = self.env.ref('base.group_user')
            group_mail_template_editor = self.env.ref('mail.group_mail_template_editor')

            if not value and group_mail_template_editor not in group_user.implied_ids:
                group_user.implied_ids |= group_mail_template_editor

            elif value and group_mail_template_editor in group_user.implied_ids:
                # remove existing users, including inactive template user
                # admin will regain the right via implied_ids on group_system
                group_user._remove_group(group_mail_template_editor)
        # sanitize and normalize allowed catchall domains
        elif key == 'mail.catchall.domain.allowed' and value:
            value = self.env['mail.alias']._sanitize_allowed_domains(value)

        return super().set_param(key, value)
