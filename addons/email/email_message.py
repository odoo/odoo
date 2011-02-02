# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>)
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

from osv import osv, fields
import time
import tools
import binascii
import email
from email.header import decode_header
from email.utils import parsedate
import base64
import re
from tools.translate import _
import logging
import xmlrpclib

_logger = logging.getLogger('mailgate')

def format_date_tz(date, tz=None):
    if not date:
        return 'n/a'
    format = tools.DEFAULT_SERVER_DATETIME_FORMAT
    return tools.server_to_local_timestamp(date, format, format, tz)

class email_message(osv.osv):
    '''
    Email Message
    '''
    _name = 'email.message'
    _description = 'Email Message'
    _order = 'date desc'

    def open_document(self, cr, uid, ids, context=None):
        """ To Open Document
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param ids: the ID of messages
        @param context: A standard dictionary
        """
        action_data = False
        if ids:
            message_id = ids[0]
            mailgate_data = self.browse(cr, uid, message_id, context=context)
            model = mailgate_data.model
            res_id = mailgate_data.res_id

            action_pool = self.pool.get('ir.actions.act_window')
            action_ids = action_pool.search(cr, uid, [('res_model', '=', model)])
            if action_ids:
                action_data = action_pool.read(cr, uid, action_ids[0], context=context)
                action_data.update({
                    'domain' : "[('id','=',%d)]"%(res_id),
                    'nodestroy': True,
                    'context': {}
                    })
        return action_data

    def open_attachment(self, cr, uid, ids, context=None):
        """ To Open attachments
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param ids: the ID of messages
        @param context: A standard dictionary
        """
        action_data = False
        action_pool = self.pool.get('ir.actions.act_window')
        message_pool = self.browse(cr ,uid, ids, context=context)[0]
        att_ids = [x.id for x in message_pool.attachment_ids]
        action_ids = action_pool.search(cr, uid, [('res_model', '=', 'ir.attachment')])
        if action_ids:
            action_data = action_pool.read(cr, uid, action_ids[0], context=context)
            action_data.update({
                'domain': [('id','in',att_ids)],
                'nodestroy': True
                })
        return action_data

    def truncate_data(self, cr, uid, data, context=None):
        data_list = data and data.split('\n') or []
        if len(data_list) > 3:
            res = '\n\t'.join(data_list[:3]) + '...'
        else:
            res = '\n\t'.join(data_list)
        return res

    def _get_display_text(self, cr, uid, ids, name, arg, context=None):
        if context is None:
            context = {}
        tz = context.get('tz')
        result = {}
        for message in self.browse(cr, uid, ids, context=context):
            msg_txt = ''
            if message.history:
                msg_txt += (message.email_from or '/') + _(' wrote on ') + format_date_tz(message.date, tz) + ':\n\t'
                if message.description:
                    msg_txt += self.truncate_data(cr, uid, message.description, context=context)
            else:
                msg_txt = (message.user_id.name or '/') + _(' on ') + format_date_tz(message.date, tz) + ':\n\t'
                if message.name == _('Opportunity'):
                    msg_txt += _("Converted to Opportunity")
                elif message.name == _('Note'):
                    msg_txt = (message.user_id.name or '/') + _(' added note on ') + format_date_tz(message.date, tz) + ':\n\t'
                    msg_txt += self.truncate_data(cr, uid, message.description, context=context)
                elif message.name == _('Stage'):
                    msg_txt += _("Changed Stage to: ") + message.description
                else:
                    msg_txt += _("Changed Status to: ") + message.name
            result[message.id] = msg_txt
        return result

    _columns = {
        'name':fields.text('Subject', readonly=True),
        'model': fields.char('Object Name', size=128, select=1, readonly=True),
        'res_id': fields.integer('Resource ID', select=1, readonly=True),
        'ref_id': fields.char('Reference Id', size=256, readonly=True, help="Message Id in Email Server.", select=True),
        'date': fields.datetime('Date', readonly=True),
        'history': fields.boolean('Is History?', readonly=True),
        'user_id': fields.many2one('res.users', 'User Responsible', readonly=True),
        'message': fields.text('Description', readonly=True),
        'email_from': fields.char('From', size=128, help="Email From", readonly=True),
        'email_to': fields.char('To', help="Email Recipients", size=256, readonly=True),
        'email_cc': fields.char('Cc', help="Carbon Copy Email Recipients", size=256, readonly=True),
        'email_bcc': fields.char('Bcc', help='Blind Carbon Copy Email Recipients', size=256, readonly=True),
        'message_id': fields.char('Message Id', size=1024, readonly=True, help="Message Id on Email.", select=True),
        'references': fields.text('References', readonly=True, help="References emails."),
        'description': fields.text('Description', readonly=True),
        'partner_id': fields.many2one('res.partner', 'Partner', required=False),
        'attachment_ids': fields.many2many('ir.attachment', 'message_attachment_rel', 'message_id', 'attachment_id', 'Attachments', readonly=True),
        'display_text': fields.function(_get_display_text, method=True, type='text', size="512", string='Display Text'),
        'reply_to':fields.char('Reply-To', size=250, readonly=True),
        'account_id' :fields.many2one('email.smtp_server', 'User account', required=True, readonly=True),
        #I like GMAIL which allows putting same mail in many folders
        #Lets plan it for 0.9
        'folder':fields.selection([
                        ('drafts', 'Drafts'),
                        ('outbox', 'Outbox'),
                        ('trash', 'Trash'),
                        ('sent', 'Sent Items'),
                        ], 'Folder', required=True, readonly=True),
        'state':fields.selection([
                        ('na', 'Not Applicable'),
                        ('sending', 'Sending'),
                        ('wait', 'Waiting'),
                        ], 'Status', required=True, readonly=True),
    }

    _defaults = {
        'state': lambda * a: 'na',
        'folder': lambda * a: 'outbox',
    }

    def unlink(self, cr, uid, ids, context=None):
        """
        It just changes the folder of the item to "Trash", if it is no in Trash folder yet,
        or completely deletes it if it is already in Trash.
        """
        to_update = []
        to_remove = []
        for mail in self.browse(cr, uid, ids, context=context):
            if mail.folder == 'trash':
                to_remove.append(mail.id)
            else:
                to_update.append(mail.id)
        # Changes the folder to trash
        self.write(cr, uid, to_update, {'folder': 'trash'}, context=context)
        return super(email_template_mailbox, self).unlink(cr, uid, to_remove, context=context)

    def init(self, cr):
        cr.execute("""SELECT indexname
                      FROM pg_indexes
                      WHERE indexname = 'email_message_res_id_model_idx'""")
        if not cr.fetchone():
            cr.execute("""CREATE INDEX email_message_res_id_model_idx
                          ON email_message (model, res_id)""")

    def run_mail_scheduler(self, cursor, user, context=None):
        """
        This method is called by OpenERP Scheduler
        to periodically send emails
        """
        try:
            self.send_all_mail(cursor, user, context=context)
        except Exception, e:
            LOGGER.notifyChannel(
                                 "Email Template",
                                 netsvc.LOG_ERROR,
                                 _("Error sending mail: %s") % e)

    def send_all_mail(self, cr, uid, ids=None, context=None):
        if ids is None:
            ids = []
        if context is None:
            context = {}
        filters = [('folder', '=', 'outbox'), ('state', '!=', 'sending')]
        if 'filters' in context.keys():
            for each_filter in context['filters']:
                filters.append(each_filter)
        ids = self.search(cr, uid, filters, context=context)
        self.write(cr, uid, ids, {'state':'sending'}, context)
        self.send_this_mail(cr, uid, ids, context)
        return True

    def send_this_mail(self, cr, uid, ids=None, context=None):
        #previous method to send email (link with email account can be found at the revision 4172 and below
        result = True
        attachment_pool = self.pool.get('ir.attachment')
        for id in (ids or []):
            try:
                account_obj = self.pool.get('email.smtp_server')
                values = self.read(cr, uid, id, [], context)
                payload = {}
                if values['attachments_ids']:
                    for attid in values['attachments_ids']:
                        attachment = attachment_pool.browse(cr, uid, attid, context)#,['datas_fname','datas'])
                        payload[attachment.datas_fname] = attachment.datas
                result = account_obj.send_mail(cr, uid,
                              [values['account_id'][0]],
                              {'To':values.get('email_to') or u'',
                               'CC':values.get('email_cc') or u'',
                               'BCC':values.get('email_bcc') or u'',
                               'Reply-To':values.get('reply_to') or u''},
                              values['subject'] or u'',
                              {'text':values.get('body_text') or u'', 'html':values.get('body_html') or u''},
                              payload=payload,
                              message_id=values['message_id'],
                              context=context)
                if result == True:
                    account = account_obj.browse(cr, uid, values['account_id'][0], context=context)
                    if account.auto_delete:
                        self.write(cr, uid, id, {'folder': 'trash'}, context=context)
                        self.unlink(cr, uid, [id], context=context)
                        # Remove attachments for this mail
                        attachment_pool.unlink(cr, uid, values['attachments_ids'], context=context)
                    else:
                        self.write(cr, uid, id, {'folder':'sent', 'state':'na', 'date_mail':time.strftime("%Y-%m-%d %H:%M:%S")}, context)
                else:
                    error = result['error_msg']

            except Exception, error:
                logger = netsvc.Logger()
                logger.notifyChannel("email-template", netsvc.LOG_ERROR, _("Sending of Mail %s failed. Probable Reason:Could not login to server\nError: %s") % (id, error))
            self.write(cr, uid, id, {'state':'na'}, context)
        return result

email_message()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
