# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import datetime
import logging
import psycopg2
import threading
import re

from collections import defaultdict
from email.utils import formataddr

from odoo import _, api, fields, models
from odoo import tools
from odoo.addons.base.models.ir_mail_server import MailDeliveryException
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)


class MailMail(models.Model):
    """ Model holding RFC2822 email messages to send. This model also provides
        facilities to queue and send new email messages.  """
    _name = 'mail.mail'
    _description = 'Outgoing Mails'
    _inherits = {'mail.message': 'mail_message_id'}
    _order = 'id desc'
    _rec_name = 'subject'

    # content
    mail_message_id = fields.Many2one('mail.message', 'Message', required=True, ondelete='cascade', index=True, auto_join=True)
    body_html = fields.Text('Rich-text Contents', help="Rich-text/HTML message")
    references = fields.Text('References', help='Message references, such as identifiers of previous messages', readonly=1)
    headers = fields.Text('Headers', copy=False)
    # Auto-detected based on create() - if 'mail_message_id' was passed then this mail is a notification
    # and during unlink() we will not cascade delete the parent and its attachments
    notification = fields.Boolean('Is Notification', help='Mail has been created to notify people of an existing mail.message')
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
    auto_delete = fields.Boolean(
        'Auto Delete',
        help="Permanently delete this email after sending it, to save space")
    failure_reason = fields.Text(
        'Failure Reason', readonly=1,
        help="Failure reason. This is usually the exception thrown by the email server, stored to ease the debugging of mailing issues.")
    scheduled_date = fields.Char('Scheduled Send Date',
        help="If set, the queue manager will send the email after the date. If not set, the email will be send as soon as possible.")

    @api.model
    def create(self, values):
        # notification field: if not set, set if mail comes from an existing mail.message
        if 'notification' not in values and values.get('mail_message_id'):
            values['notification'] = True
        return super(MailMail, self).create(values)

    @api.multi
    def unlink(self):
        # cascade-delete the parent message for all mails that are not created for a notification
        mail_msg_cascade_ids = [mail.mail_message_id.id for mail in self if not mail.notification]
        res = super(MailMail, self).unlink()
        if mail_msg_cascade_ids:
            self.env['mail.message'].browse(mail_msg_cascade_ids).unlink()
        return res

    @api.model
    def default_get(self, fields):
        # protection for `default_type` values leaking from menu action context (e.g. for invoices)
        # To remove when automatic context propagation is removed in web client
        if self._context.get('default_type') not in type(self).message_type.base_field.selection:
            self = self.with_context(dict(self._context, default_type=None))
        return super(MailMail, self).default_get(fields)

    @api.multi
    def mark_outgoing(self):
        return self.write({'state': 'outgoing'})

    @api.multi
    def cancel(self):
        return self.write({'state': 'cancel'})

    @api.model
    def process_email_queue(self, ids=None):
        """Send immediately queued messages, committing after each
           message is sent - this is not transactional and should
           not be called during another transaction!

           :param list ids: optional list of emails ids to send. If passed
                            no search is performed, and these ids are used
                            instead.
           :param dict context: if a 'filters' key is present in context,
                                this value will be used as an additional
                                filter to further restrict the outgoing
                                messages to send (by default all 'outgoing'
                                messages are sent).
        """
        filters = ['&',
                   ('state', '=', 'outgoing'),
                   '|',
                   ('scheduled_date', '<', datetime.datetime.now()),
                   ('scheduled_date', '=', False)]
        if 'filters' in self._context:
            filters.extend(self._context['filters'])
        # TODO: make limit configurable
        filtered_ids = self.search(filters, limit=10000).ids
        if not ids:
            ids = filtered_ids
        else:
            ids = list(set(filtered_ids) & set(ids))
        ids.sort()

        res = None
        try:
            # auto-commit except in testing mode
            auto_commit = not getattr(threading.currentThread(), 'testing', False)
            res = self.browse(ids).send(auto_commit=auto_commit)
        except Exception:
            _logger.exception("Failed processing mail queue")
        return res

    @api.multi
    def _postprocess_sent_message(self, success_pids, failure_reason=False, failure_type=None):
        """Perform any post-processing necessary after sending ``mail``
        successfully, including deleting it completely along with its
        attachment if the ``auto_delete`` flag of the mail was set.
        Overridden by subclasses for extra post-processing behaviors.

        :return: True
        """
        notif_mails_ids = [mail.id for mail in self if mail.notification]
        if notif_mails_ids:
            notifications = self.env['mail.notification'].search([
                ('is_email', '=', True),
                ('mail_id', 'in', notif_mails_ids),
                ('email_status', 'not in', ('sent', 'canceled'))
            ])
            if notifications:
                #find all notification linked to a failure
                failed = self.env['mail.notification']
                if failure_type:
                    failed = notifications.filtered(lambda notif: notif.res_partner_id not in success_pids)
                    failed.write({
                        'email_status': 'exception',
                        'failure_type': failure_type,
                        'failure_reason': failure_reason,
                    })
                    messages = notifications.mapped('mail_message_id').filtered(lambda m: m.res_id and m.model)
                    messages._notify_failure_update()  # notify user that we have a failure
                (notifications - failed).write({
                    'email_status': 'sent',
                })
        if not failure_type or failure_type == 'RECIPIENT':  # if we have another error, we want to keep the mail.
            mail_to_delete_ids = [mail.id for mail in self if mail.auto_delete]
            self.browse(mail_to_delete_ids).sudo().unlink()
        return True

    # ------------------------------------------------------
    # mail_mail formatting, tools and send mechanism
    # ------------------------------------------------------

    @api.multi
    def _send_prepare_body(self):
        """Return a specific ir_email body. The main purpose of this method
        is to be inherited to add custom content depending on some module."""
        self.ensure_one()
        return self.body_html or ''

    @api.multi
    def _send_prepare_values(self, partner=None):
        """Return a dictionary for specific email values, depending on a
        partner, or generic to the whole recipients given by mail.email_to.

            :param Model partner: specific recipient partner
        """
        self.ensure_one()
        body = self._send_prepare_body()
        body_alternative = tools.html2plaintext(body)
        if partner:
            email_to = [formataddr((partner.name or 'False', partner.email or 'False'))]
        else:
            email_to = tools.email_split_and_format(self.email_to)
        res = {
            'body': body,
            'body_alternative': body_alternative,
            'email_to': email_to,
        }
        return res

    @api.multi
    def _split_by_server(self):
        """Returns an iterator of pairs `(mail_server_id, record_ids)` for current recordset.

        The same `mail_server_id` may repeat in order to limit batch size according to
        the `mail.session.batch.size` system parameter.
        """
        groups = defaultdict(list)
        # Turn prefetch OFF to avoid MemoryError on very large mail queues, we only care
        # about the mail server ids in this case.
        for mail in self.with_context(prefetch_fields=False):
            groups[mail.mail_server_id.id].append(mail.id)
        sys_params = self.env['ir.config_parameter'].sudo()
        batch_size = int(sys_params.get_param('mail.session.batch.size', 1000))
        for server_id, record_ids in groups.items():
            for mail_batch in tools.split_every(batch_size, record_ids):
                yield server_id, mail_batch

    @api.multi
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
        for server_id, batch_ids in self._split_by_server():
            smtp_session = None
            try:
                smtp_session = self.env['ir.mail_server'].connect(mail_server_id=server_id)
            except Exception as exc:
                if raise_exception:
                    # To be consistent and backward compatible with mail_mail.send() raised
                    # exceptions, it is encapsulated into an Odoo MailDeliveryException
                    raise MailDeliveryException(_('Unable to connect to SMTP Server'), exc)
                else:
                    batch = self.browse(batch_ids)
                    batch.write({'state': 'exception', 'failure_reason': exc})
                    batch._postprocess_sent_message(success_pids=[], failure_type="SMTP")
            else:
                self.browse(batch_ids)._send(
                    auto_commit=auto_commit,
                    raise_exception=raise_exception,
                    smtp_session=smtp_session)
                _logger.info(
                    'Sent batch %s emails via mail server ID #%s',
                    len(batch_ids), server_id)
            finally:
                if smtp_session:
                    smtp_session.quit()

    @api.multi
    def _send(self, auto_commit=False, raise_exception=False, smtp_session=None):
        IrMailServer = self.env['ir.mail_server']
        IrAttachment = self.env['ir.attachment']
        for mail_id in self.ids:
            success_pids = []
            failure_type = None
            processing_pid = None
            mail = None
            try:
                mail = self.browse(mail_id)
                if mail.state != 'outgoing':
                    if mail.state != 'exception' and mail.auto_delete:
                        mail.sudo().unlink()
                    continue

                # remove attachments if user send the link with the access_token
                body = mail.body_html or ''
                attachments = mail.attachment_ids
                for link in re.findall(r'/web/(?:content|image)/([0-9]+)', body):
                    attachments = attachments - IrAttachment.browse(int(link))

                # load attachment binary data with a separate read(), as prefetching all
                # `datas` (binary field) could bloat the browse cache, triggerring
                # soft/hard mem limits with temporary data.
                attachments = [(a['datas_fname'], base64.b64decode(a['datas']), a['mimetype'])
                               for a in attachments.sudo().read(['datas_fname', 'datas', 'mimetype'])]

                # specific behavior to customize the send email for notified partners
                email_list = []
                if mail.email_to:
                    email_list.append(mail._send_prepare_values())
                for partner in mail.recipient_ids:
                    values = mail._send_prepare_values(partner=partner)
                    values['partner_id'] = partner
                    email_list.append(values)

                # headers
                headers = {}
                ICP = self.env['ir.config_parameter'].sudo()
                bounce_alias = ICP.get_param("mail.bounce.alias")
                catchall_domain = ICP.get_param("mail.catchall.domain")
                if bounce_alias and catchall_domain:
                    if mail.model and mail.res_id:
                        headers['Return-Path'] = '%s+%d-%s-%d@%s' % (bounce_alias, mail.id, mail.model, mail.res_id, catchall_domain)
                    else:
                        headers['Return-Path'] = '%s+%d@%s' % (bounce_alias, mail.id, catchall_domain)
                if mail.headers:
                    try:
                        headers.update(safe_eval(mail.headers))
                    except Exception:
                        pass

                # Writing on the mail object may fail (e.g. lock on user) which
                # would trigger a rollback *after* actually sending the email.
                # To avoid sending twice the same email, provoke the failure earlier
                mail.write({
                    'state': 'exception',
                    'failure_reason': _('Error without exception. Probably due do sending an email without computed recipients.'),
                })
                # Update notification in a transient exception state to avoid concurrent
                # update in case an email bounces while sending all emails related to current
                # mail record.
                notifs = self.env['mail.notification'].search([
                    ('is_email', '=', True),
                    ('mail_id', 'in', mail.ids),
                    ('email_status', 'not in', ('sent', 'canceled'))
                ])
                if notifs:
                    notif_msg = _('Error without exception. Probably due do concurrent access update of notification records. Please see with an administrator.')
                    notifs.write({
                        'email_status': 'exception',
                        'failure_type': 'UNKNOWN',
                        'failure_reason': notif_msg,
                    })

                # build an RFC2822 email.message.Message object and send it without queuing
                res = None
                for email in email_list:
                    msg = IrMailServer.build_email(
                        email_from=mail.email_from,
                        email_to=email.get('email_to'),
                        subject=mail.subject,
                        body=email.get('body'),
                        body_alternative=email.get('body_alternative'),
                        email_cc=tools.email_split(mail.email_cc),
                        reply_to=mail.reply_to,
                        attachments=attachments,
                        message_id=mail.message_id,
                        references=mail.references,
                        object_id=mail.res_id and ('%s-%s' % (mail.res_id, mail.model)),
                        subtype='html',
                        subtype_alternative='plain',
                        headers=headers)
                    processing_pid = email.pop("partner_id", None)
                    try:
                        res = IrMailServer.send_email(
                            msg, mail_server_id=mail.mail_server_id.id, smtp_session=smtp_session)
                        if processing_pid:
                            success_pids.append(processing_pid)
                        processing_pid = None
                    except AssertionError as error:
                        if str(error) == IrMailServer.NO_VALID_RECIPIENT:
                            failure_type = "RECIPIENT"
                            # No valid recipient found for this particular
                            # mail item -> ignore error to avoid blocking
                            # delivery to next recipients, if any. If this is
                            # the only recipient, the mail will show as failed.
                            _logger.info("Ignoring invalid recipients for mail.mail %s: %s",
                                         mail.message_id, email.get('email_to'))
                        else:
                            raise
                if res:  # mail has been sent at least once, no major exception occured
                    mail.write({'state': 'sent', 'message_id': res, 'failure_reason': False})
                    _logger.info('Mail with ID %r and Message-Id %r successfully sent', mail.id, mail.message_id)
                    # /!\ can't use mail.state here, as mail.refresh() will cause an error
                    # see revid:odo@openerp.com-20120622152536-42b2s28lvdv3odyr in 6.1
                mail._postprocess_sent_message(success_pids=success_pids, failure_type=failure_type)
            except UnicodeEncodeError as exc:
                _logger.exception('UnicodeEncodeError on text "%s" while processing mail ID %r.', exc.object, mail.id)
                raise MailDeliveryException(_("Mail Delivery Failed"), "Invalid text: %s" % exc.object)
            except MemoryError:
                # prevent catching transient MemoryErrors, bubble up to notify user or abort cron job
                # instead of marking the mail as failed
                _logger.exception(
                    'MemoryError while processing mail with ID %r and Msg-Id %r. Consider raising the --limit-memory-hard startup option',
                    mail.id, mail.message_id)
                # mail status will stay on ongoing since transaction will be rollback
                raise
            except psycopg2.Error:
                # If an error with the database occurs, chances are that the cursor is unusable.
                # This will lead to an `psycopg2.InternalError` being raised when trying to write
                # `state`, shadowing the original exception and forbid a retry on concurrent
                # update. Let's bubble it.
                raise
            except Exception as e:
                failure_reason = tools.ustr(e)
                _logger.exception('failed sending mail (id: %s) due to %s', mail.id, failure_reason)
                mail.write({'state': 'exception', 'failure_reason': failure_reason})
                mail._postprocess_sent_message(success_pids=success_pids, failure_reason=failure_reason, failure_type='UNKNOWN')
                if raise_exception:
                    if isinstance(e, AssertionError):
                        # get the args of the original error, wrap into a value and throw a MailDeliveryException
                        # that is an except_orm, with name and value as arguments
                        value = '. '.join(e.args)
                        raise MailDeliveryException(_("Mail Delivery Failed"), value)
                    raise

            if auto_commit is True:
                self._cr.commit()
        return True
