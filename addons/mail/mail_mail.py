# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2010-today OpenERP SA (<http://www.openerp.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################

import base64
import logging
import re
from urllib import urlencode
from urlparse import urljoin

from openerp import tools
from openerp import SUPERUSER_ID
from openerp.addons.base.ir.ir_mail_server import MailDeliveryException
from openerp.osv import fields, osv
from openerp.tools.translate import _

_logger = logging.getLogger(__name__)


class mail_mail(osv.Model):
    """ Model holding RFC2822 email messages to send. This model also provides
        facilities to queue and send new email messages.  """
    _name = 'mail.mail'
    _description = 'Outgoing Mails'
    _inherits = {'mail.message': 'mail_message_id'}
    _order = 'id desc'
    _rec_name = 'subject'

    _columns = {
        'mail_message_id': fields.many2one('mail.message', 'Message', required=True, ondelete='cascade'),
        'state': fields.selection([
            ('outgoing', 'Outgoing'),
            ('sent', 'Sent'),
            ('received', 'Received'),
            ('exception', 'Delivery Failed'),
            ('cancel', 'Cancelled'),
        ], 'Status', readonly=True),
        'auto_delete': fields.boolean('Auto Delete',
            help="Permanently delete this email after sending it, to save space"),
        'references': fields.text('References', help='Message references, such as identifiers of previous messages', readonly=1),
        'email_to': fields.text('To', help='Message recipients (emails)'),
        'recipient_ids': fields.many2many('res.partner', string='To (Partners)'),
        'email_cc': fields.char('Cc', help='Carbon copy message recipients'),
        'body_html': fields.text('Rich-text Contents', help="Rich-text/HTML message"),
        # Auto-detected based on create() - if 'mail_message_id' was passed then this mail is a notification
        # and during unlink() we will not cascade delete the parent and its attachments
        'notification': fields.boolean('Is Notification',
            help='Mail has been created to notify people of an existing mail.message'),
    }

    _defaults = {
        'state': 'outgoing',
    }

    def default_get(self, cr, uid, fields, context=None):
        # protection for `default_type` values leaking from menu action context (e.g. for invoices)
        # To remove when automatic context propagation is removed in web client
        if context and context.get('default_type') and context.get('default_type') not in self._all_columns['type'].column.selection:
            context = dict(context, default_type=None)
        return super(mail_mail, self).default_get(cr, uid, fields, context=context)

    def create(self, cr, uid, values, context=None):
        # notification field: if not set, set if mail comes from an existing mail.message
        if 'notification' not in values and values.get('mail_message_id'):
            values['notification'] = True
        return super(mail_mail, self).create(cr, uid, values, context=context)

    def unlink(self, cr, uid, ids, context=None):
        # cascade-delete the parent message for all mails that are not created for a notification
        ids_to_cascade = self.search(cr, uid, [('notification', '=', False), ('id', 'in', ids)])
        parent_msg_ids = [m.mail_message_id.id for m in self.browse(cr, uid, ids_to_cascade, context=context)]
        res = super(mail_mail, self).unlink(cr, uid, ids, context=context)
        self.pool.get('mail.message').unlink(cr, uid, parent_msg_ids, context=context)
        return res

    def mark_outgoing(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'outgoing'}, context=context)

    def cancel(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'cancel'}, context=context)

    def process_email_queue(self, cr, uid, ids=None, context=None):
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
        if context is None:
            context = {}
        if not ids:
            filters = [('state', '=', 'outgoing')]
            if 'filters' in context:
                filters.extend(context['filters'])
            ids = self.search(cr, uid, filters, context=context)
        res = None
        try:
            # Force auto-commit - this is meant to be called by
            # the scheduler, and we can't allow rolling back the status
            # of previously sent emails!
            res = self.send(cr, uid, ids, auto_commit=True, context=context)
        except Exception:
            _logger.exception("Failed processing mail queue")
        return res

    def _postprocess_sent_message(self, cr, uid, mail, context=None, mail_sent=True):
        """Perform any post-processing necessary after sending ``mail``
        successfully, including deleting it completely along with its
        attachment if the ``auto_delete`` flag of the mail was set.
        Overridden by subclasses for extra post-processing behaviors.

        :param browse_record mail: the mail that was just sent
        :return: True
        """
        if mail_sent and mail.auto_delete:
            # done with SUPERUSER_ID to avoid giving large unlink access rights
            self.unlink(cr, SUPERUSER_ID, [mail.id], context=context)
        return True

    #------------------------------------------------------
    # mail_mail formatting, tools and send mechanism
    #------------------------------------------------------

    def _get_partner_access_link(self, cr, uid, mail, partner=None, context=None):
        """Generate URLs for links in mails: partner has access (is user):
        link to action_mail_redirect action that will redirect to doc or Inbox """
        if context is None:
            context = {}
        if partner and partner.user_ids:
            base_url = self.pool.get('ir.config_parameter').get_param(cr, uid, 'web.base.url')
            mail_model = mail.model or 'mail.thread'
            url = urljoin(base_url, self.pool[mail_model]._get_access_link(cr, uid, mail, partner, context=context))
            return _("""<span class='oe_mail_footer_access'><small>about <a style='color:inherit' href="%s">%s %s</a></small></span>""") % (url, context.get('model_name', ''), mail.record_name)
        else:
            return None

    def send_get_mail_subject(self, cr, uid, mail, force=False, partner=None, context=None):
        """If subject is void, set the subject as 'Re: <Resource>' or
        'Re: <mail.parent_id.subject>'

            :param boolean force: force the subject replacement
        """
        if (force or not mail.subject) and mail.record_name:
            return 'Re: %s' % (mail.record_name)
        elif (force or not mail.subject) and mail.parent_id and mail.parent_id.subject:
            return 'Re: %s' % (mail.parent_id.subject)
        return mail.subject

    def send_get_mail_body(self, cr, uid, mail, partner=None, context=None):
        """Return a specific ir_email body. The main purpose of this method
        is to be inherited to add custom content depending on some module."""
        body = mail.body_html

        # generate footer
        link = self._get_partner_access_link(cr, uid, mail, partner, context=context)
        if link:
            body = tools.append_content_to_html(body, link, plaintext=False, container_tag='div')
        return body

    def send_get_mail_to(self, cr, uid, mail, partner=None, context=None):
        """Forge the email_to with the following heuristic:
          - if 'partner' and mail is a notification on a document: followers (Followers of 'Doc' <email>)
          - elif 'partner', no notificatoin or no doc: recipient specific (Partner Name <email>)
          - else fallback on mail.email_to splitting """
        if partner and mail.notification and mail.record_name:
            sanitized_record_name = re.sub(r'[^\w+.]+', '-', mail.record_name)
            email_to = [_('"Followers of %s" <%s>') % (sanitized_record_name, partner.email)]
        elif partner:
            email_to = ['%s <%s>' % (partner.name, partner.email)]
        else:
            email_to = tools.email_split(mail.email_to)
        return email_to

    def send_get_email_dict(self, cr, uid, mail, partner=None, context=None):
        """Return a dictionary for specific email values, depending on a
        partner, or generic to the whole recipients given by mail.email_to.

            :param browse_record mail: mail.mail browse_record
            :param browse_record partner: specific recipient partner
        """
        body = self.send_get_mail_body(cr, uid, mail, partner=partner, context=context)
        body_alternative = tools.html2plaintext(body)
        res = {
            'body': body,
            'body_alternative': body_alternative,
            'subject': self.send_get_mail_subject(cr, uid, mail, partner=partner, context=context),
            'email_to': self.send_get_mail_to(cr, uid, mail, partner=partner, context=context),
        }
        if mail.model and mail.res_id and self.pool.get(mail.model) and hasattr(self.pool[mail.model], 'message_get_email_values'):
            res.update(self.pool[mail.model].message_get_email_values(cr, uid, mail.res_id, mail, context=context))
        return res

    def send(self, cr, uid, ids, auto_commit=False, raise_exception=False, context=None):
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
        if context is None:
            context = {}
        ir_mail_server = self.pool.get('ir.mail_server')
        ir_attachment = self.pool['ir.attachment']
        for mail in self.browse(cr, SUPERUSER_ID, ids, context=context):
            try:
                # TDE note: remove me when model_id field is present on mail.message - done here to avoid doing it multiple times in the sub method
                if mail.model:
                    model_id = self.pool['ir.model'].search(cr, SUPERUSER_ID, [('model', '=', mail.model)], context=context)[0]
                    model = self.pool['ir.model'].browse(cr, SUPERUSER_ID, model_id, context=context)
                else:
                    model = None
                if model:
                    context['model_name'] = model.name

                # load attachment binary data with a separate read(), as prefetching all
                # `datas` (binary field) could bloat the browse cache, triggerring
                # soft/hard mem limits with temporary data.
                attachment_ids = [a.id for a in mail.attachment_ids]
                attachments = [(a['datas_fname'], base64.b64decode(a['datas']))
                                 for a in ir_attachment.read(cr, SUPERUSER_ID, attachment_ids,
                                                             ['datas_fname', 'datas'])]

                # specific behavior to customize the send email for notified partners
                email_list = []
                if mail.email_to:
                    email_list.append(self.send_get_email_dict(cr, uid, mail, context=context))
                for partner in mail.recipient_ids:
                    email_list.append(self.send_get_email_dict(cr, uid, mail, partner=partner, context=context))
                # headers
                headers = {}
                bounce_alias = self.pool['ir.config_parameter'].get_param(cr, uid, "mail.bounce.alias", context=context)
                catchall_domain = self.pool['ir.config_parameter'].get_param(cr, uid, "mail.catchall.domain", context=context)
                if bounce_alias and catchall_domain:
                    if mail.model and mail.res_id:
                        headers['Return-Path'] = '%s-%d-%s-%d@%s' % (bounce_alias, mail.id, mail.model, mail.res_id, catchall_domain)
                    else:
                        headers['Return-Path'] = '%s-%d@%s' % (bounce_alias, mail.id, catchall_domain)

                # build an RFC2822 email.message.Message object and send it without queuing
                res = None
                for email in email_list:
                    email_headers = dict(headers)
                    if email.get('headers'):
                        email_headers.update(email['headers'])
                    msg = ir_mail_server.build_email(
                        email_from=mail.email_from,
                        email_to=email.get('email_to'),
                        subject=email.get('subject'),
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
                        headers=email_headers)
                    res = ir_mail_server.send_email(cr, uid, msg,
                                                    mail_server_id=mail.mail_server_id.id,
                                                    context=context)

                if res:
                    mail.write({'state': 'sent', 'message_id': res})
                    mail_sent = True
                else:
                    mail.write({'state': 'exception'})
                    mail_sent = False

                # /!\ can't use mail.state here, as mail.refresh() will cause an error
                # see revid:odo@openerp.com-20120622152536-42b2s28lvdv3odyr in 6.1
                self._postprocess_sent_message(cr, uid, mail, context=context, mail_sent=mail_sent)
                _logger.info('Mail with ID %r and Message-Id %r successfully sent', mail.id, mail.message_id)
            except MemoryError:
                # prevent catching transient MemoryErrors, bubble up to notify user or abort cron job
                # instead of marking the mail as failed
                _logger.exception('MemoryError while processing mail with ID %r and Msg-Id %r. '\
                                      'Consider raising the --limit-memory-hard startup option',
                                  mail.id, mail.message_id)
                raise
            except Exception as e:
                _logger.exception('failed sending mail.mail %s', mail.id)
                mail.write({'state': 'exception'})
                self._postprocess_sent_message(cr, uid, mail, context=context, mail_sent=False)
                if raise_exception:
                    if isinstance(e, AssertionError):
                        # get the args of the original error, wrap into a value and throw a MailDeliveryException
                        # that is an except_orm, with name and value as arguments
                        value = '. '.join(e.args)
                        raise MailDeliveryException(_("Mail Delivery Failed"), value)
                    raise

            if auto_commit is True:
                cr.commit()
        return True
