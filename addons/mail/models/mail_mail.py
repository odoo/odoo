# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast
import base64
import datetime
import logging
import psycopg2
import smtplib
import threading
import re
import pytz

from collections import defaultdict
from dateutil.parser import parse

from odoo import _, api, fields, models
from odoo import tools
from odoo.addons.base.models.ir_mail_server import MailDeliveryException

_logger = logging.getLogger(__name__)
_UNFOLLOW_REGEX = re.compile(r'<span id="mail_unfollow".*?<\/span>', re.DOTALL)


class MailMail(models.Model):
    """ Model holding RFC2822 email messages to send. This model also provides
        facilities to queue and send new email messages.  """
    _name = 'mail.mail'
    _description = 'Outgoing Mails'
    _inherits = {'mail.message': 'mail_message_id'}
    _order = 'id desc'
    _rec_name = 'subject'

    @api.model
    def default_get(self, fields):
        # protection for `default_type` values leaking from menu action context (e.g. for invoices)
        # To remove when automatic context propagation is removed in web client
        if self._context.get('default_type') not in self._fields['message_type'].base_field.selection:
            self = self.with_context(dict(self._context, default_type=None))
        if self._context.get('default_state') not in self._fields['state'].base_field.selection:
            self = self.with_context(dict(self._context, default_state='outgoing'))
        return super(MailMail, self).default_get(fields)

    # content
    mail_message_id = fields.Many2one('mail.message', 'Message', required=True, ondelete='cascade', index=True, auto_join=True)
    mail_message_id_int = fields.Integer(compute='_compute_mail_message_id_int', compute_sudo=True)
    message_type = fields.Selection(related='mail_message_id.message_type', inherited=True, default='email_outgoing')
    body_html = fields.Text('Text Contents', help="Rich-text/HTML message")
    body_content = fields.Html('Rich-text Contents', sanitize=True, compute='_compute_body_content', search="_search_body_content")
    references = fields.Text('References', help='Message references, such as identifiers of previous messages', readonly=True)
    headers = fields.Text('Headers', copy=False)
    restricted_attachment_count = fields.Integer('Restricted attachments', compute='_compute_restricted_attachments')
    unrestricted_attachment_ids = fields.Many2many('ir.attachment', string='Unrestricted Attachments',
        compute='_compute_restricted_attachments', inverse='_inverse_unrestricted_attachment_ids')
    # Auto-detected based on create() - if 'mail_message_id' was passed then this mail is a notification
    # and during unlink() we will not cascade delete the parent and its attachments
    is_notification = fields.Boolean('Notification Email', help='Mail has been created to notify people of an existing mail.message')
    # recipients: include inactive partners (they may have been archived after
    # the message was sent, but they should remain visible in the relation)
    email_to = fields.Text('To', help='Message recipients (emails)')
    email_cc = fields.Char('Cc', help='Carbon copy message recipients')
    recipient_ids = fields.Many2many('res.partner', string='To (Partners)',
        context={'active_test': False})
    # process
    state = fields.Selection([
        ('outgoing', 'Outgoing'),
        ('sent', 'Sent'),
        ('received', 'Received'),
        ('exception', 'Delivery Failed'),
        ('cancel', 'Cancelled'),
    ], 'Status', readonly=True, copy=False, default='outgoing')
    failure_type = fields.Selection(selection=[
        # generic
        ("unknown", "Unknown error"),
        # mail
        ("mail_email_invalid", "Invalid email address"),
        ("mail_email_missing", "Missing email"),
        ("mail_from_invalid", "Invalid from address"),
        ("mail_from_missing", "Missing from address"),
        ("mail_smtp", "Connection failed (outgoing mail server problem)"),
        # mass mode
        ("mail_bl", "Blacklisted Address"),
        ("mail_optout", "Opted Out"),
        ("mail_dup", "Duplicated Email"),
        ], string='Failure type')
    failure_reason = fields.Text(
        'Failure Reason', readonly=True, copy=False,
        help="Failure reason. This is usually the exception thrown by the email server, stored to ease the debugging of mailing issues.")
    auto_delete = fields.Boolean(
        'Auto Delete',
        help="This option permanently removes any track of email after it's been sent, including from the Technical menu in the Settings, in order to preserve storage space of your Odoo database.")
    scheduled_date = fields.Datetime('Scheduled Send Date',
        help="If set, the queue manager will send the email after the date. If not set, the email will be send as soon as possible. Unless a timezone is specified, it is considered as being in UTC timezone.")
    fetchmail_server_id = fields.Many2one('fetchmail.server', "Inbound Mail Server", readonly=True)

    def _compute_body_content(self):
        for mail in self:
            mail.body_content = mail.body_html

    def _compute_mail_message_id_int(self):
        for mail in self:
            mail.mail_message_id_int = mail.mail_message_id.id

    @api.depends('attachment_ids')
    def _compute_restricted_attachments(self):
        """We might not have access to all the attachments of the emails.
        Compute the attachments we have access to,
        and the number of attachments we do not have access to.
        """
        IrAttachment = self.env['ir.attachment']
        for mail_sudo, mail in zip(self.sudo(), self):
            mail.unrestricted_attachment_ids = IrAttachment._filter_attachment_access(mail_sudo.attachment_ids.ids)
            mail.restricted_attachment_count = len(mail_sudo.attachment_ids) - len(mail.unrestricted_attachment_ids)

    def _inverse_unrestricted_attachment_ids(self):
        """We can only remove the attachments we have access to."""
        IrAttachment = self.env['ir.attachment']
        for mail_sudo, mail in zip(self.sudo(), self):
            restricted_attaments = mail_sudo.attachment_ids - IrAttachment._filter_attachment_access(mail_sudo.attachment_ids.ids)
            mail_sudo.attachment_ids = restricted_attaments | mail.unrestricted_attachment_ids

    def _search_body_content(self, operator, value):
        return [('body_html', operator, value)]

    @api.model
    def fields_get(self, *args, **kwargs):
        # related selection will fetch translations from DB
        # selections added in stable won't be in DB -> add them on the related model if not already added
        message_type_field = self.env['mail.message']._fields['message_type']
        if 'auto_comment' not in {value for value, name in message_type_field.get_description(self.env)['selection']}:
            self._fields_get_message_type_update_selection(message_type_field.selection)
        return super().fields_get(*args, **kwargs)

    def _fields_get_message_type_update_selection(self, selection):
        """Update the field selection for message type on mail.message to match the runtime values.

        DO NOT USE it is only there for a stable fix and should not be used for any reason other than hotfixing.
        """
        self.env['ir.model.fields'].invalidate_model(['selection_ids'])
        self.env['ir.model.fields.selection'].sudo()._update_selection('mail.message', 'message_type', selection)
        self.env.registry.clear_cache()

    @api.model_create_multi
    def create(self, values_list):
        # notification field: if not set, set if mail comes from an existing mail.message
        for values in values_list:
            if 'is_notification' not in values and values.get('mail_message_id'):
                values['is_notification'] = True
            if values.get('scheduled_date'):
                parsed_datetime = self._parse_scheduled_datetime(values['scheduled_date'])
                values['scheduled_date'] = parsed_datetime.replace(tzinfo=None) if parsed_datetime else False
            else:
                values['scheduled_date'] = False  # void string crashes
        new_mails = super(MailMail, self).create(values_list)

        new_mails_w_attach = self.env['mail.mail']
        for mail, values in zip(new_mails, values_list):
            if values.get('attachment_ids'):
                new_mails_w_attach += mail
        if new_mails_w_attach:
            new_mails_w_attach.mapped('attachment_ids').check(mode='read')

        return new_mails

    def write(self, vals):
        if vals.get('scheduled_date'):
            parsed_datetime = self._parse_scheduled_datetime(vals['scheduled_date'])
            vals['scheduled_date'] = parsed_datetime.replace(tzinfo=None) if parsed_datetime else False
        res = super(MailMail, self).write(vals)
        if vals.get('attachment_ids'):
            for mail in self:
                mail.attachment_ids.check(mode='read')
        return res

    def unlink(self):
        # cascade-delete the parent message for all mails that are not created for a notification
        mail_msg_cascade_ids = [mail.mail_message_id.id for mail in self if not mail.is_notification]
        res = super(MailMail, self).unlink()
        if mail_msg_cascade_ids:
            self.env['mail.message'].browse(mail_msg_cascade_ids).unlink()
        return res

    @api.model
    def _add_inherited_fields(self):
        """Allow to bypass ACLs for some mail message fields.

        This trick add a related_sudo on the inherits fields, it can't be done with
        >>> subject = fields.Char(related='mail_message_id.subject', related_sudo=True)
        because the field of <mail.message> will be fetched two times (one time before of
        the inherits, and a second time because of the related), and so it will add extra
        SQL queries.
        """
        super()._add_inherited_fields()
        for field in ('email_from', 'reply_to', 'subject'):
            self._fields[field].related_sudo = True

    def action_retry(self):
        self.filtered(lambda mail: mail.state == 'exception').mark_outgoing()

    def action_open_document(self):
        """ Opens the related record based on the model and ID """
        self.ensure_one()
        return {
            'res_id': self.res_id,
            'res_model': self.model,
            'target': 'current',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
        }

    def mark_outgoing(self):
        return self.write({'state': 'outgoing'})

    def cancel(self):
        return self.write({'state': 'cancel'})

    @api.model
    def process_email_queue(self, ids=None):
        """Send immediately queued messages, committing after each
           message is sent - this is not transactional and should
           not be called during another transaction!

        A maximum of 10K MailMail (configurable using 'mail.mail.queue.batch.size'
        optional ICP) are fetched in order to keep time under control.

        :param list ids: optional list of emails ids to send. If given only
                         scheduled and outgoing emails within this ids list
                         are sent;
        :param dict context: if a 'filters' key is present in context,
                             this value will be used as an additional
                             filter to further restrict the outgoing
                             messages to send (by default all 'outgoing'
                             'scheduled' messages are sent).
        """
        domain = [
            '&',
                ('state', '=', 'outgoing'),
                '|',
                   ('scheduled_date', '=', False),
                   ('scheduled_date', '<=', datetime.datetime.utcnow()),
        ]
        if 'filters' in self._context:
            domain.extend(self._context['filters'])
        batch_size = int(self.env['ir.config_parameter'].sudo().get_param('mail.mail.queue.batch.size', 10000))
        send_ids = self.search(domain, limit=batch_size).ids
        if ids:
            send_ids = list(set(send_ids) & set(ids))
        send_ids.sort()

        res = None
        try:
            # auto-commit except in testing mode
            auto_commit = not getattr(threading.current_thread(), 'testing', False)
            res = self.browse(send_ids).send(auto_commit=auto_commit)
        except Exception:
            _logger.exception("Failed processing mail queue")

        return res

    def _postprocess_sent_message(self, success_pids, failure_reason=False, failure_type=None):
        """Perform any post-processing necessary after sending ``mail``
        successfully, including deleting it completely along with its
        attachment if the ``auto_delete`` flag of the mail was set.
        Overridden by subclasses for extra post-processing behaviors.

        :return: True
        """
        notif_mails_ids = [mail.id for mail in self if mail.is_notification]
        if notif_mails_ids:
            notifications = self.env['mail.notification'].search([
                ('notification_type', '=', 'email'),
                ('mail_mail_id', 'in', notif_mails_ids),
                ('notification_status', 'not in', ('sent', 'canceled'))
            ])
            if notifications:
                # find all notification linked to a failure
                failed = self.env['mail.notification']
                if failure_type:
                    failed = notifications.filtered(lambda notif: notif.res_partner_id not in success_pids)
                (notifications - failed).sudo().write({
                    'notification_status': 'sent',
                    'failure_type': '',
                    'failure_reason': '',
                })
                if failed:
                    failed.sudo().write({
                        'notification_status': 'exception',
                        'failure_type': failure_type,
                        'failure_reason': failure_reason,
                    })
                    messages = notifications.mapped('mail_message_id').filtered(lambda m: m.is_thread_message())
                    # TDE TODO: could be great to notify message-based, not notifications-based, to lessen number of notifs
                    messages._notify_message_notification_update()  # notify user that we have a failure
        if not failure_type or failure_type in ['mail_email_invalid', 'mail_email_missing']:  # if we have another error, we want to keep the mail.
            self.sudo().filtered(lambda mail: mail.auto_delete).unlink()

        return True

    def _parse_scheduled_datetime(self, scheduled_datetime):
        """ Taking an arbitrary datetime (either as a date, a datetime or a string)
        try to parse it and return a datetime timezoned to UTC.

        If no specific timezone information is given, we consider it as being
        given in UTC, as all datetime values given to the server. Trying to
        guess its timezone based on user or flow would be strange as this is
        not standard. When manually creating datetimes for mail.mail scheduled
        date, business code should ensure either a timezone info is set, either
        it is converted into UTC.

        Using yearfirst when parsing str datetimes eases parser's job when
        dealing with the hard-to-parse trio (01/04/09 -> ?). In most use cases
        year will be given first as this is the expected default formatting.

        :return datetime: parsed datetime (or False if parser failed)
        """
        if isinstance(scheduled_datetime, datetime.datetime):
            parsed_datetime = scheduled_datetime
        elif isinstance(scheduled_datetime, datetime.date):
            parsed_datetime = datetime.combine(scheduled_datetime, datetime.time.min)
        else:
            try:
                parsed_datetime = parse(scheduled_datetime, yearfirst=True)
            except (ValueError, TypeError):
                parsed_datetime = False
        if parsed_datetime:
            parsed_datetime = parsed_datetime.replace(microsecond=0)
            if not parsed_datetime.tzinfo:
                parsed_datetime = pytz.utc.localize(parsed_datetime)
            else:
                try:
                    parsed_datetime = parsed_datetime.astimezone(pytz.utc)
                except Exception:
                    pass
        return parsed_datetime

    # ------------------------------------------------------
    # mail_mail formatting, tools and send mechanism
    # ------------------------------------------------------

    def _prepare_outgoing_body(self):
        """Return a specific ir_email body. The main purpose of this method
        is to be inherited to add custom content depending on some module."""
        self.ensure_one()
        if tools.is_html_empty(self.body_html):
            return ''
        return self.env['mail.render.mixin']._replace_local_links(self.body_html)

    def _personalize_outgoing_body(self, body, partner=False, recipients_follower_status=None):
        """ Return a modified body based on the recipient (partner).

        It must be called when using standard notification layouts
        even for message without partners.

        :param str body: body to personalize for the recipient
        :param partner: <res.partner> recipient
        :param set recipients_follower_status: see ``Followers._get_mail_recipients_follower_status()``
        """
        self.ensure_one()

        if (recipients_follower_status and '/mail/unfollow' in body and partner and
                self.model and self.res_id and (self.model, self.res_id, partner.id) in recipients_follower_status and
                (getattr(self.env[self.model], '_partner_unfollow_enabled', False) or
                 any(user._is_internal() for user in partner.user_ids))):
            unfollow_url = self.env['mail.thread']._notify_get_action_link(
                'unfollow', model=self.model, res_id=self.res_id, pid=partner.id)
            body = body.replace('/mail/unfollow', unfollow_url)
        else:
            body = re.sub(_UNFOLLOW_REGEX, '', body)
        return body

    def _prepare_outgoing_list(self, recipients_follower_status=None):
        """ Return a list of emails to send based on current mail.mail. Each
        is a dictionary for specific email values, depending on a partner, or
        generic to the whole recipients given by mail.email_to.

        :param set recipients_follower_status: see ``Followers._get_mail_recipients_follower_status()``
        :return list: list of dicts used in IrMailServer.build_email()
        """
        self.ensure_one()
        body = self._prepare_outgoing_body()

        # headers
        headers = {}
        if self.headers:
            try:
                headers = ast.literal_eval(self.headers)
            except (ValueError, TypeError) as e:
                _logger.warning(
                    'Evaluation error when evaluating mail headers (received %r): %s',
                    self.headers, e,
                )
            # global except as we don't want to crash the queue just due to a malformed
            # headers value
            except Exception as e:
                _logger.warning(
                    'Unknown error when evaluating mail headers (received %r): %s',
                    self.headers, e,
                )
        headers['X-Odoo-Message-Id'] = self.message_id
        headers.setdefault('Return-Path', self.record_alias_domain_id.bounce_email or self.env.company.bounce_email)

        # prepare recipients: use email_to if defined then check recipient_ids
        # that receive a specific email, notably due to link shortening / redirect
        # that is recipients-dependent. Keep original email/partner as this is
        # used in post-processing to know failures, like missing recipients
        email_list = []
        if self.email_to:
            email_to_normalized = tools.email_normalize_all(self.email_to)
            email_to = tools.email_split_and_format_normalize(self.email_to)
            email_list.append({
                'email_cc': [],
                'email_to': email_to,
                # list of normalized emails to help extract_rfc2822
                'email_to_normalized': email_to_normalized,
                # keep raw initial value for incoming pre processing of outgoing emails
                'email_to_raw': self.email_to or '',
                'partner_id': False,
            })
        # add all cc once, either to the first "To", either as a single entry (do not mix
        # with partner-specific sending)
        if self.email_cc:
            if email_list:
                email_list[0]['email_cc'] = tools.email_split_and_format_normalize(self.email_cc)
                email_list[0]['email_to_normalized'] += tools.email_normalize_all(self.email_cc)
            else:
                email_list.append({
                    'email_cc':  tools.email_split_and_format_normalize(self.email_cc),
                    'email_to': [],
                    'email_to_normalized': tools.email_normalize_all(self.email_cc),
                    'email_to_raw': False,
                    'partner_id': False,
                })
        # specific behavior to customize the send email for notified partners
        for partner in self.recipient_ids:
            # check partner email content
            email_to_normalized = tools.email_normalize_all(partner.email)
            email_to = [
                tools.formataddr((partner.name or "", email or "False"))
                for email in email_to_normalized or [partner.email]
            ]
            email_list.append({
                'email_cc': [],
                'email_to': email_to,
                # list of normalized emails to help extract_rfc2822
                'email_to_normalized': email_to_normalized,
                # keep raw initial value for incoming pre processing of outgoing emails
                'email_to_raw': partner.email or '',
                'partner_id': partner,
            })

        # prepare attachments: remove attachments if user send the link with the
        # access_token.
        attachments = self.attachment_ids
        if attachments:
            if body:
                link_ids = {int(link) for link in re.findall(r'/web/(?:content|image)/([0-9]+)', body)}
                if link_ids:
                    attachments = attachments - self.env['ir.attachment'].browse(list(link_ids))
            # load attachment binary data with a separate read(), as prefetching all
            # `datas` (binary field) could bloat the browse cache, triggering
            # soft/hard mem limits with temporary data.
            email_attachments = [
                (a['name'], base64.b64decode(a['datas']), a['mimetype'])
                for a in attachments.sudo().read(['name', 'datas', 'mimetype']) if a['datas'] is not False
            ]
        else:
            email_attachments = []

        # Build final list of email values with personalized body for recipient
        results = []
        for email_values in email_list:
            partner_id = email_values['partner_id']
            body_personalized = self._personalize_outgoing_body(body, partner_id, recipients_follower_status)
            results.append({
                'attachments': email_attachments,
                'body': body_personalized,
                'body_alternative': tools.html2plaintext(body_personalized),
                'email_cc': email_values['email_cc'],
                'email_from': self.email_from,
                'email_to': email_values['email_to'],
                'email_to_normalized': email_values['email_to_normalized'],
                'email_to_raw': email_values['email_to_raw'],
                'headers': headers,
                'message_id': self.message_id,
                'object_id': f'{self.res_id}-{self.model}' if self.res_id else '',
                'partner_id': partner_id,
                'references': self.references,
                'reply_to': self.reply_to,
                'subject': self.subject,
            })

        return results

    def _split_by_mail_configuration(self):
        """Group the <mail.mail> based on their "email_from", their "alias domain"
        and their "mail_server_id".

        The <mail.mail> will have the "same sending configuration" if they have the same
        mail server, alias domain and mail from. For performance purpose, we can use an SMTP
        session in batch and therefore we need to group them by the parameter that will
        influence the mail server used.

        The same "sending configuration" may repeat in order to limit batch size
        according to the `mail.session.batch.size` system parameter.

        Return iterators over
            mail_server_id, email_from, Records<mail.mail>.ids
        """
        mail_values = self.read(['id', 'email_from', 'mail_server_id', 'record_alias_domain_id'])

        # First group the <mail.mail> per mail_server_id, per alias_domain (if no server) and per email_from
        group_per_email_from = defaultdict(list)
        for values in mail_values:
            # protect against ill-formatted email_from when formataddr was used on an already formatted email
            emails_from = tools.email_split_and_format_normalize(values['email_from'])
            email_from = emails_from[0] if emails_from else values['email_from']
            mail_server_id = values['mail_server_id'][0] if values['mail_server_id'] else False
            alias_domain_id = values['record_alias_domain_id'][0] if values['record_alias_domain_id'] else False
            key = (mail_server_id, alias_domain_id, email_from)
            group_per_email_from[key].append(values['id'])

        # Then find the mail server for each email_from and group the <mail.mail>
        # per mail_server_id and smtp_from
        mail_servers = self.env['ir.mail_server'].sudo().search([], order='sequence, id')
        group_per_smtp_from = defaultdict(list)
        for (mail_server_id, alias_domain_id, email_from), mail_ids in group_per_email_from.items():
            if not mail_server_id:
                mail_server = self.env['ir.mail_server']
                if alias_domain_id:
                    alias_domain = self.env['mail.alias.domain'].sudo().browse(alias_domain_id)
                    mail_server = mail_server.with_context(
                        domain_notifications_email=alias_domain.default_from_email,
                        domain_bounce_address=alias_domain.bounce_email,
                    )
                mail_server, smtp_from = mail_server._find_mail_server(email_from, mail_servers)
                mail_server_id = mail_server.id if mail_server else False
            else:
                smtp_from = email_from

            group_per_smtp_from[(mail_server_id, alias_domain_id, smtp_from)].extend(mail_ids)

        batch_size = int(self.env['ir.config_parameter'].sudo().get_param('mail.session.batch.size')) or 1000
        for (mail_server_id, alias_domain_id, smtp_from), record_ids in group_per_smtp_from.items():
            for batch_ids in tools.split_every(batch_size, record_ids):
                yield mail_server_id, alias_domain_id, smtp_from, batch_ids

    def send(self, auto_commit=False, raise_exception=False):
        """ Sends the selected emails immediately, ignoring their current
            state (mails that have already been sent should not be passed
            unless they should actually be re-sent).
            Emails successfully delivered are marked as 'sent', and those
            that fail to be deliver are marked as 'exception', and the
            corresponding error mail is output in the server logs.

            :param bool auto_commit: whether to force a commit of the mail status
                after sending each mail (meant only for scheduler processing);
                should never be True during normal transactions (default: False)
            :param bool raise_exception: whether to raise an exception if the
                email sending process has failed
            :return: True
        """
        for mail_server_id, alias_domain_id, smtp_from, batch_ids in self._split_by_mail_configuration():
            smtp_session = None
            try:
                smtp_session = self.env['ir.mail_server'].connect(mail_server_id=mail_server_id, smtp_from=smtp_from)
            except Exception as exc:
                if raise_exception:
                    # To be consistent and backward compatible with mail_mail.send() raised
                    # exceptions, it is encapsulated into an Odoo MailDeliveryException
                    raise MailDeliveryException(_('Unable to connect to SMTP Server'), exc)
                else:
                    batch = self.browse(batch_ids)
                    batch.write({'state': 'exception', 'failure_reason': exc})
                    batch._postprocess_sent_message(success_pids=[], failure_type="mail_smtp")
            else:
                self.browse(batch_ids)._send(
                    auto_commit=auto_commit,
                    raise_exception=raise_exception,
                    smtp_session=smtp_session,
                    alias_domain_id=alias_domain_id,
                )
                _logger.info(
                    'Sent batch %s emails via mail server ID #%s',
                    len(batch_ids), mail_server_id)
            finally:
                if smtp_session:
                    smtp_session.quit()

    def _send(self, auto_commit=False, raise_exception=False, smtp_session=None, alias_domain_id=False):
        IrMailServer = self.env['ir.mail_server']
        # Only retrieve recipient followers of the mails if needed
        mails_with_unfollow_link = self.filtered(lambda m: m.body_html and '/mail/unfollow' in m.body_html)
        recipients_follower_status = (
            None if not mails_with_unfollow_link
            else self.env['mail.followers']._get_mail_recipients_follower_status(mails_with_unfollow_link.ids)
        )

        for mail_id in self.ids:
            success_pids = []
            failure_reason = None
            failure_type = None
            processing_pid = None
            mail = None
            try:
                mail = self.browse(mail_id)
                if mail.state != 'outgoing':
                    continue

                # Writing on the mail object may fail (e.g. lock on user) which
                # would trigger a rollback *after* actually sending the email.
                # To avoid sending twice the same email, provoke the failure earlier
                mail.write({
                    'state': 'exception',
                    'failure_reason': _('Error without exception. Probably due to sending an email without computed recipients.'),
                })
                # Update notification in a transient exception state to avoid concurrent
                # update in case an email bounces while sending all emails related to current
                # mail record.
                notifs = self.env['mail.notification'].search([
                    ('notification_type', '=', 'email'),
                    ('mail_mail_id', 'in', mail.ids),
                    ('notification_status', 'not in', ('sent', 'canceled'))
                ])
                if notifs:
                    notif_msg = _('Error without exception. Probably due to concurrent access update of notification records. Please see with an administrator.')
                    notifs.sudo().write({
                        'notification_status': 'exception',
                        'failure_type': 'unknown',
                        'failure_reason': notif_msg,
                    })
                    # `test_mail_bounce_during_send`, force immediate update to obtain the lock.
                    # see rev. 56596e5240ef920df14d99087451ce6f06ac6d36
                    notifs.flush_recordset(['notification_status', 'failure_type', 'failure_reason'])

                # protect against ill-formatted email_from when formataddr was used on an already formatted email
                emails_from = tools.email_split_and_format_normalize(mail.email_from)
                email_from = emails_from[0] if emails_from else mail.email_from

                # build an RFC2822 email.message.Message object and send it without queuing
                res = None
                # TDE note: could be great to pre-detect missing to/cc and skip sending it
                # to go directly to failed state update
                email_list = mail._prepare_outgoing_list(recipients_follower_status)

                # send each sub-email
                for email in email_list:
                    # give indication to 'send_mail' about emails already considered
                    # as being valid
                    email_to_normalized = email.pop('email_to_normalized', [])
                    # if given, contextualize sending using alias domains
                    if alias_domain_id:
                        alias_domain = self.env['mail.alias.domain'].sudo().browse(alias_domain_id)
                        SendIrMailServer = IrMailServer.with_context(
                            domain_notifications_email=alias_domain.default_from_email,
                            domain_bounce_address=email['headers'].get('Return-Path') or alias_domain.bounce_email,
                            send_validated_to=email_to_normalized,
                        )
                    else:
                        SendIrMailServer = IrMailServer.with_context(send_validated_to=email_to_normalized)
                    msg = SendIrMailServer.build_email(
                        email_from=email_from,
                        email_to=email['email_to'],
                        subject=email['subject'],
                        body=email['body'],
                        body_alternative=email['body_alternative'],
                        email_cc=email['email_cc'],
                        reply_to=email['reply_to'],
                        attachments=email['attachments'],
                        message_id=email['message_id'],
                        references=email['references'],
                        object_id=email['object_id'],
                        subtype='html',
                        subtype_alternative='plain',
                        headers=email['headers'],
                    )
                    processing_pid = email.pop("partner_id", None)
                    try:
                        res = SendIrMailServer.send_email(
                            msg, mail_server_id=mail.mail_server_id.id, smtp_session=smtp_session)
                        if processing_pid:
                            success_pids.append(processing_pid)
                        processing_pid = None
                    except AssertionError as error:
                        if str(error) == IrMailServer.NO_VALID_RECIPIENT:
                            # if we have a list of void emails for email_list -> email missing, otherwise generic email failure
                            if not email.get('email_to') and failure_type != "mail_email_invalid":
                                failure_type = "mail_email_missing"
                            else:
                                failure_type = "mail_email_invalid"
                            # No valid recipient found for this particular
                            # mail item -> ignore error to avoid blocking
                            # delivery to next recipients, if any. If this is
                            # the only recipient, the mail will show as failed.
                            _logger.info("Ignoring invalid recipients for mail.mail %s: %s",
                                         mail.message_id, email.get('email_to'))
                        else:
                            raise
                if res:  # mail has been sent at least once, no major exception occurred
                    mail.write({'state': 'sent', 'message_id': res, 'failure_reason': False})
                    _logger.info('Mail with ID %r and Message-Id %r successfully sent', mail.id, mail.message_id)
                    # /!\ can't use mail.state here, as mail.refresh() will cause an error
                    # see revid:odo@openerp.com-20120622152536-42b2s28lvdv3odyr in 6.1
                mail._postprocess_sent_message(success_pids=success_pids, failure_type=failure_type)
            except MemoryError:
                # prevent catching transient MemoryErrors, bubble up to notify user or abort cron job
                # instead of marking the mail as failed
                _logger.exception(
                    'MemoryError while processing mail with ID %r and Msg-Id %r. Consider raising the --limit-memory-hard startup option',
                    mail.id, mail.message_id)
                # mail status will stay on ongoing since transaction will be rollback
                raise
            except (psycopg2.Error, smtplib.SMTPServerDisconnected):
                # If an error with the database or SMTP session occurs, chances are that the cursor
                # or SMTP session are unusable, causing further errors when trying to save the state.
                _logger.exception(
                    'Exception while processing mail with ID %r and Msg-Id %r.',
                    mail.id, mail.message_id)
                raise
            except Exception as e:
                if isinstance(e, AssertionError):
                    # Handle assert raised in IrMailServer to try to catch notably from-specific errors.
                    # Note that assert may raise several args, a generic error string then a specific
                    # message for logging in failure type
                    error_code = e.args[0]
                    if len(e.args) > 1 and error_code == IrMailServer.NO_VALID_FROM:
                        # log failing email in additional arguments message
                        failure_reason = tools.ustr(e.args[1])
                    else:
                        failure_reason = error_code
                    if error_code == IrMailServer.NO_VALID_FROM:
                        failure_type = "mail_from_invalid"
                    elif error_code in (IrMailServer.NO_FOUND_FROM, IrMailServer.NO_FOUND_SMTP_FROM):
                        failure_type = "mail_from_missing"
                # generic (unknown) error as fallback
                if not failure_reason:
                    failure_reason = tools.ustr(e)
                if not failure_type:
                    failure_type = "unknown"

                _logger.exception('failed sending mail (id: %s) due to %s', mail.id, failure_reason)
                mail.write({
                    "failure_reason": failure_reason,
                    "failure_type": failure_type,
                    "state": "exception",
                })
                mail._postprocess_sent_message(
                    success_pids=success_pids,
                    failure_reason=failure_reason, failure_type=failure_type
                )
                if raise_exception:
                    if isinstance(e, (AssertionError, UnicodeEncodeError)):
                        if isinstance(e, UnicodeEncodeError):
                            value = "Invalid text: %s" % e.object
                        else:
                            value = '. '.join(e.args)
                        raise MailDeliveryException(value)
                    raise

            if auto_commit is True:
                self._cr.commit()
        return True
