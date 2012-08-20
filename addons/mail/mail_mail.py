
import ast
import base64
import email
import logging
import re
import time
import datetime

from osv import osv
from osv import fields

class mail_mail(osv.Model):
    """
    Model holding RFC2822 email messages to send. This model also provides
    facilities to queue and send new email messages. 
    """

    _name = 'mail.mail'
    _description = 'Outgoing Mails'
    _inherits = {'mail.message': 'mail_message_id'}
    _columns = {
        'mail_message_id': fields.many2one('mail.message', 'Message', required=True, ondelete='cascade'),
        'mail_server_id': fields.many2one('ir.mail_server', 'Outgoing mail server', readonly=1),
        'subject': fields.char('Subject', size=128),
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
        'email_from': fields.char('From', size=128, help='Message sender, taken from user preferences.'),
        'email_to': fields.text('To', help='Message recipients'),
        'email_cc': fields.char('Cc', size=256, help='Carbon copy message recipients'),
        'reply_to':fields.char('Reply-To', size=256, help='Preferred response address for the message'),

        'content_subtype': fields.char('Message content subtype', size=32,
            oldname="subtype", readonly=1,
            help="Type of message, usually 'html' or 'plain', used to select "\
                  "plain-text or rich-text contents accordingly"),
        'body_html': fields.text('Rich-text Contents', help="Rich-text/HTML version of the message"),
    }

    _defaults = {
        'state': 'outgoing',
        'content_subtype': 'plain',
    }

    def mark_outgoing(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state':'outgoing'}, context=context)

    def cancel(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state':'cancel'}, context=context)

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
            filters = ['&', ('state', '=', 'outgoing'), ('type', '=', 'email')]
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

    def _postprocess_sent_message(self, cr, uid, message, context=None):
        """Perform any post-processing necessary after sending ``message``
        successfully, including deleting it completely along with its
        attachment if the ``auto_delete`` flag of the message was set.
        Overridden by subclasses for extra post-processing behaviors. 

        :param browse_record message: the message that was just sent
        :return: True
        """
        if message.auto_delete:
            self.pool.get('ir.attachment').unlink(cr, uid,
                [x.id for x in message.attachment_ids],
                context=context)
            message.unlink()
        return True

    def send(self, cr, uid, ids, auto_commit=False, context=None):
        """Sends the selected emails immediately, ignoring their current
           state (mails that have already been sent should not be passed
           unless they should actually be re-sent).
           Emails successfully delivered are marked as 'sent', and those
           that fail to be deliver are marked as 'exception', and the
           corresponding error message is output in the server logs.

           :param bool auto_commit: whether to force a commit of the message
                                    status after sending each message (meant
                                    only for processing by the scheduler),
                                    should never be True during normal
                                    transactions (default: False)
           :return: True
        """
        ir_mail_server = self.pool.get('ir.mail_server')
        self.write(cr, uid, ids, {'state': 'outgoing'}, context=context)
        for message in self.browse(cr, uid, ids, context=context):
            try:
                attachments = []
                for attach in message.attachment_ids:
                    attachments.append((attach.datas_fname, base64.b64decode(attach.datas)))

                body = message.body_html if message.content_subtype == 'html' else message.body
                body_alternative = None
                content_subtype_alternative = None
                if message.content_subtype == 'html' and message.body:
                    # we have a plain text alternative prepared, pass it to 
                    # build_message instead of letting it build one
                    body_alternative = message.body
                    content_subtype_alternative = 'plain'

                # handle destination_partners
                partner_ids_email_to = ''
                for partner in message.partner_ids:
                    partner_ids_email_to += '%s ' % (partner.email or '')
                message_email_to = '%s %s' % (partner_ids_email_to, message.email_to or '')

                # build an RFC2822 email.message.Message object and send it
                # without queuing
                msg = ir_mail_server.build_email(
                    email_from=message.email_from,
                    email_to=tools.email_split(message_email_to),
                    subject=message.subject,
                    body=body,
                    body_alternative=body_alternative,
                    email_cc=tools.email_split(message.email_cc),
                    reply_to=message.reply_to,
                    attachments=attachments, message_id=message.message_id,
                    references = message.references,
                    object_id=message.res_id and ('%s-%s' % (message.res_id,message.model)),
                    subtype=message.content_subtype,
                    subtype_alternative=content_subtype_alternative,
                    headers=message.headers and ast.literal_eval(message.headers))
                res = ir_mail_server.send_email(cr, uid, msg,
                                                mail_server_id=message.mail_server_id.id,
                                                context=context)
                if res:
                    message.write({'state':'sent', 'message_id': res, 'email_to': message_email_to})
                else:
                    message.write({'state':'exception', 'email_to': message_email_to})
                message.refresh()
                if message.state == 'sent':
                    self._postprocess_sent_message(cr, uid, message, context=context)
            except Exception:
                _logger.exception('failed sending mail.message %s', message.id)
                message.write({'state':'exception'})

            if auto_commit == True:
                cr.commit()
        return True

