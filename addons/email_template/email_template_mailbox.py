# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2009 Sharoon Thomas
#    Copyright (C) 2004-2010 OpenERP SA (<http://www.openerp.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################

from osv import osv, fields
import time
import netsvc
from tools.translate import _
import tools

LOGGER = netsvc.Logger()

class email_template_mailbox(osv.osv):
    _name = "email_template.mailbox"
    _description = 'Email Mailbox'
    _rec_name = "subject"
    _order = "date_mail desc"
    
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
                account_obj = self.pool.get('email_template.account')
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
                        return result
                    else:
                        self.write(cr, uid, id, {'folder':'sent', 'state':'na', 'date_mail':time.strftime("%Y-%m-%d %H:%M:%S")}, context)
                        self.historise(cr, uid, [id], "Email sent successfully", context)
                else:
                    error = result['error_msg']
                    self.historise(cr, uid, [id], error, context)
                    
            except Exception, error:
                logger = netsvc.Logger()
                logger.notifyChannel("email-template", netsvc.LOG_ERROR, _("Sending of Mail %s failed. Probable Reason:Could not login to server\nError: %s") % (id, error))
                self.historise(cr, uid, [id], error, context)
            self.write(cr, uid, id, {'state':'na'}, context)
        return result
    
    def historise(self, cr, uid, ids, message='', context=None):
        for id in ids:
            history = self.read(cr, uid, id, ['history'], context).get('history', '')
            self.write(cr, uid, id, {'history': (history or '' )+ "\n" + time.strftime("%Y-%m-%d %H:%M:%S") + ": " + tools.ustr(message)}, context)
    
    _columns = {
            'email_from':fields.char(
                            'From', 
                            size=64),
            'email_to':fields.char(
                            'Recipient (To)', 
                            size=250,),
            'email_cc':fields.char(
                            'CC', 
                            size=250),
            'email_bcc':fields.char(
                            'BCC', 
                            size=250),
            'reply_to':fields.char(
                            'Reply-To', 
                            size=250),
            'message_id':fields.char(
                            'Message-ID', 
                            size=250),
            'subject':fields.char(
                            'Subject', 
                            size=200,),
            'body_text':fields.text(
                            'Standard Body (Text)'),
            'body_html':fields.text(
                            'Body (Rich Text Clients Only)'),
            'attachments_ids':fields.many2many(
                            'ir.attachment', 
                            'mail_attachments_rel', 
                            'mail_id', 
                            'att_id', 
                            'Attachments'),
            'account_id' :fields.many2one(
                            'email_template.account',
                            'User account', 
                            required=True),
            'user':fields.related(
                            'account_id', 
                            'user', 
                            type="many2one", 
                            relation="res.users", 
                            string="User"),
            'server_ref':fields.integer(
                            'Server Reference of mail', 
                            help="Applicable for inward items only"),
            'mail_type':fields.selection([
                            ('multipart/mixed', 
                             'Has Attachments'),
                            ('multipart/alternative', 
                             'Plain Text & HTML with no attachments'),
                            ('multipart/related', 
                             'Intermixed content'),
                            ('text/plain', 
                             'Plain Text'),
                            ('text/html', 
                             'HTML Body'),
                            ], 'Mail Contents'),
            #I like GMAIL which allows putting same mail in many folders
            #Lets plan it for 0.9
            'folder':fields.selection([
                            ('drafts', 'Drafts'),
                            ('outbox', 'Outbox'),
                            ('trash', 'Trash'),
                            ('sent', 'Sent Items'),
                            ], 'Folder', required=True),
            'state':fields.selection([
                            ('na', 'Not Applicable'),
                            ('sending', 'Sending'),
                            ], 'Status', required=True),
            'date_mail':fields.datetime('Rec/Sent Date', help="Date on which Email Sent or Received"),
            'history':fields.text(
                            'History', 
                            readonly=True, 
                            store=True)
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

email_template_mailbox()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
