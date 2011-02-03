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

from osv import osv
from osv import fields
from tools.translate import _
import tools

#import time
#import binascii
#import email
#from email.header import decode_header
#from email.utils import parsedate
#import base64
#import re
#import logging
#import xmlrpclib

#_logger = logging.getLogger('mailgate')

#import re
#import smtplib
#import base64
#from email import Encoders
#from email.mime.base import MIMEBase
#from email.mime.multipart import MIMEMultipart
#from email.mime.text import MIMEText
#from email.header import decode_header, Header
#from email.utils import formatdate
#import netsvc
#import datetime
#import tools
#import logging

#EMAIL_PATTERN = re.compile(r'([^()\[\] ,<:\\>@";]+@[^()\[\] ,<:\\>@";]+)') # See RFC822
#def extract_emails(emails_str):
#    """
#    Returns a list of email addresses recognized in a string, ignoring the rest of the string.
#    extract_emails('a@b.com,c@bcom, "John Doe" <d@b.com> , e@b.com') -> ['a@b.com','c@bcom', 'd@b.com', 'e@b.com']"
#    """
#    return EMAIL_PATTERN.findall(emails_str)
#
#
#def extract_emails_from_dict(addresses={}):
#    """
#    Extracts email addresses from a dictionary with comma-separated address string values, handling
#    separately the To, CC, BCC and Reply-To addresses.
#
#    :param addresses: a dictionary of addresses in the form {'To': 'a@b.com,c@bcom; d@b.com;e@b.com' , 'CC': 'e@b.com;f@b.com', ... }
#    :return: a dictionary with a list of separate addresses for each header (To, CC, BCC), with an additional key 'all-recipients'
#             containing all addresses for the 'To', 'CC', 'BCC' entries.
#    """
#    result = {'all-recipients':[]}
#    keys = ['To', 'CC', 'BCC', 'Reply-To']
#    for each in keys:
#        emails = extract_emails(addresses.get(each, u''))
#        while u'' in emails:
#            emails.remove(u'')
#        result[each] = emails
#        if each != 'Reply-To':
#            result['all-recipients'].extend(emails)
#    return result

class email_smtp_server(osv.osv):
    """
    Object to store email account settings
    """
    _name = "email.smtp_server"
    _known_content_types = ['multipart/mixed',
                            'multipart/alternative',
                            'multipart/related',
                            'text/plain',
                            'text/html'
                            ]
    _columns = {
        'name': fields.char('Description',
                        size=64, required=True,
                        readonly=True, select=True,
                        help="The description is used as the Sender name along with the provided From Email, \
unless it is already specified in the From Email, e.g: John Doe <john@doe.com>",
                        states={'draft':[('readonly', False)]}),
        'email_id': fields.char('From Email',
                        size=120, required=True,
                        readonly=True, states={'draft':[('readonly', False)]} ,
                        help="eg: 'john@doe.com' or 'John Doe <john@doe.com>'"),
        'smtpserver': fields.char('Server',
                        size=120, required=True,
                        readonly=True, states={'draft':[('readonly', False)]},
                        help="Enter name of outgoing server, eg: smtp.yourdomain.com"),
        'smtpport': fields.integer('SMTP Port',
                        size=64, required=True,
                        readonly=True, states={'draft':[('readonly', False)]},
                        help="Enter port number, eg: 25 or 587"),
        'smtpuname': fields.char('User Name',
                        size=120, required=False,
                        readonly=True, states={'draft':[('readonly', False)]},
                        help="Specify the username if your SMTP server requires authentication, "
                        "otherwise leave it empty."),
        'smtppass': fields.char('Password',
                        size=120, invisible=True,
                        required=False, readonly=True,
                        states={'draft':[('readonly', False)]}),
        'smtptls':fields.boolean('TLS',
                        states={'draft':[('readonly', False)]}, readonly=True),

        'smtpssl':fields.boolean('SSL/TLS (only in python 2.6)',
                        states={'draft':[('readonly', False)]}, readonly=True),
        'state':fields.selection([
                                  ('draft', 'Initiated'),
                                  ('suspended', 'Suspended'),
                                  ('approved', 'Approved')
                                  ],
                        'State', required=True, readonly=True),
        'default': fields.boolean('Default', help="Only one account can be default at a time"),
    }

    _defaults = {
         'name':lambda self, cursor, user, context:self.pool.get( 'res.users'
                                                ).read(cursor, user, user, ['name'], context)['name'],
         'state':lambda * a:'draft',
         'smtpport':lambda *a:25,
         'smtpserver':lambda *a:'localhost',
         'smtptls':lambda *a:True,
     }

    _sql_constraints = [
        (
         'email_uniq',
         'unique (email_id)',
         'Another setting already exists with this email ID !')
    ]

    def _constraint_unique(self, cr, uid, ids, context=None):
        default_ids = self.search(cr, uid, [('default','=',True)])
        print "default_ids::",default_ids
        if len(default_ids) > 1:
            return False
        elif not default_ids:
            return False
        else:
            return True

    _constraints = [
        (_constraint_unique,
         'Error: You must be define one default smtp server account !.',
         [])
    ]

    def name_get(self, cr, uid, ids, context=None):
        return [(a["id"], "%s (%s)" % (a['email_id'], a['name'])) for a in self.read(cr, uid, ids, ['name', 'email_id'], context=context)]

    def email_send(cr, uid, email_from, email_to, subject, body, model=False, email_cc=None, email_bcc=None, reply_to=False, attach=None,
            openobject_id=False, debug=False, subtype='plain', x_headers=None, priority='3', smtp_id=False):
        attachment_obj = self.pool.get('ir.attachment')
        email_msg_obj = self.pool.get('email.message')
        msg_vals = {
                'name': subject,
                'model': model or '',
                'date': time.strftime('%Y-%m-%d'),
                'user_id': uid,
                'message': body,
                'email_from': email_from,
                'email_to': email_to or '',
                'email_cc': email_cc or '',
                'email_bcc': email_bcc or '',
                'reply_to': reply_to or '',
                'message_id': openobject_id,
                'account_id': smtp_id,
                'sub_type': subtype or '',
                'x_headers': x_headers or '',
                'priority': priority,
                'debug': debug,
                'folder': 'outbox',
                'state': 'waiting',
            }
        email_msg_id = self.create(cr, uid, msg_vals, context)
        if attach:
            for attachment in attach:
                attachment_data = {
                        'name':  (subject or '') + _(' (Email Attachment)'),
                        'datas': attachment[1],
                        'datas_fname': attachment[0],
                        'description': subject or _('No Description'),
                        'res_model':'email.message',
                        'res_id': email_msg_id,
                    }
                attachment_id = attachment_obj.create(cr, uid, attachment_data, context)
                if attachment_id:
                    email_msg_obj.write(cr, uid, email_msg_id,
                                      { 'attachments_ids':[(4, attachment_id)] }, context)
        return True



#    def get_outgoing_server(self, cursor, user, ids, context=None):
#        """
#        Returns the Out Going Connection (SMTP) object
#
#        @attention: DO NOT USE except_osv IN THIS METHOD
#        @param cursor: Database Cursor
#        @param user: ID of current user
#        @param ids: ID/list of ids of current object for
#                    which connection is required
#                    First ID will be chosen from lists
#        @param context: Context
#
#        @return: SMTP server object or Exception
#        """
#        #Type cast ids to integer
#        if type(ids) == list:
#            ids = ids[0]
#        this_object = self.browse(cursor, user, ids, context=context)
#        if this_object:
#            if this_object.smtpserver and this_object.smtpport:
#                try:
#                    if this_object.smtpssl:
#                        serv = smtplib.SMTP_SSL(this_object.smtpserver, this_object.smtpport)
#                    else:
#                        serv = smtplib.SMTP(this_object.smtpserver, this_object.smtpport)
#                    if this_object.smtptls:
#                        serv.ehlo()
#                        serv.starttls()
#                        serv.ehlo()
#                except Exception, error:
#                    raise error
#                try:
#                    if serv.has_extn('AUTH') or this_object.smtpuname or this_object.smtppass:
#                        serv.login(str(this_object.smtpuname), str(this_object.smtppass))
#                except Exception, error:
#                    raise error
#                return serv
#            raise Exception(_("SMTP SERVER or PORT not specified"))
#        raise Exception(_("Core connection for the given ID does not exist"))
#
#    def check_outgoing_connection(self, cursor, user, ids, context=None):
#        """
#        checks SMTP credentials and confirms if outgoing connection works
#        (Attached to button)
#        @param cursor: Database Cursor
#        @param user: ID of current user
#        @param ids: list of ids of current object for
#                    which connection is required
#        @param context: Context
#        """
#        try:
#            self.get_outgoing_server(cursor, user, ids, context)
#            raise osv.except_osv(_("SMTP Test Connection Was Successful"), '')
#        except osv.except_osv, success_message:
#            raise success_message
#        except Exception, error:
#            raise osv.except_osv(
#                                 _("Out going connection test failed"),
#                                 _("Reason: %s") % error
#                                 )
#
#    def do_approval(self, cr, uid, ids, context=None):
#        #TODO: Check if user has rights
#        self.write(cr, uid, ids, {'state':'approved'}, context=context)
##        wf_service = netsvc.LocalService("workflow")
#
#    def smtp_connection(self, cursor, user, id, context=None):
#        """
#        This method should now wrap smtp_connection
#        """
#        #This function returns a SMTP server object
#        logger = netsvc.Logger()
#        core_obj = self.browse(cursor, user, id, context=context)
#        if core_obj.smtpserver and core_obj.smtpport and core_obj.state == 'approved':
#            try:
#                serv = self.get_outgoing_server(cursor, user, id, context)
#            except Exception, error:
#                logger.notifyChannel(_("Email Template"), netsvc.LOG_ERROR, _("Mail from Account %s failed on login. Probable Reason:Could not login to server\nError: %s") % (id, error))
#                return False
#            #Everything is complete, now return the connection
#            return serv
#        else:
#            logger.notifyChannel(_("Email Template"), netsvc.LOG_ERROR, _("Mail from Account %s failed. Probable Reason:Account not approved") % id)
#            return False
#
##**************************** MAIL SENDING FEATURES ***********************#
#    def send_email(self, cr, uid, ids, addresses, subject='', body=None, payload=None, message_id=None, context=None):
#        #TODO: Replace all this with a single email object
#        if body is None:
#            body = {}
#        if payload is None:
#            payload = {}
#        if context is None:
#            context = {}
#        logger = netsvc.Logger()
#        for id in ids:
#            core_obj = self.browse(cr, uid, id, context)
#            serv = self.smtp_connection(cr, uid, id)
#            if serv:
#                try:
#                    # Need a multipart/mixed wrapper for attachments if content is alternative
#                    if payload:
#                        payload_part = MIMEMultipart(_subtype='mixed')
#                        text_part = MIMEMultipart(_subtype='mixed')
#                        payload_part.attach(text_part)
#                    else:
#                        # otherwise a single multipart/mixed will do the whole job
#                        payload_part = text_part = MIMEMultipart(_subtype='mixed')
#
#                    if subject:
#                        payload_part['Subject'] = subject
#                    from_email = core_obj.email_id
#                    if '<' in from_email:
#                        # We have a structured email address, keep it untouched
#                        payload_part['From'] = Header(core_obj.email_id, 'utf-8').encode()
#                    else:
#                        # Plain email address, construct a structured one based on the name:
#                        sender_name = Header(core_obj.name, 'utf-8').encode()
#                        payload_part['From'] = sender_name + " <" + core_obj.email_id + ">"
#                    payload_part['Organization'] = tools.ustr(core_obj.user.company_id.name)
#                    payload_part['Date'] = formatdate()
#                    addresses_l = extract_emails_from_dict(addresses)
#                    if addresses_l['To']:
#                        payload_part['To'] = u','.join(addresses_l['To'])
#                    if addresses_l['CC']:
#                        payload_part['CC'] = u','.join(addresses_l['CC'])
#                    if addresses_l['Reply-To']:
#                        payload_part['Reply-To'] = addresses_l['Reply-To'][0]
#                    if message_id:
#                        payload_part['Message-ID'] = message_id
#                    if body.get('text', False):
#                        temp_body_text = body.get('text', '')
#                        l = len(temp_body_text.replace(' ', '').replace('\r', '').replace('\n', ''))
#                        if l == 0:
#                            body['text'] = u'No Mail Message'
#                    # Attach parts into message container.
#                    # According to RFC 2046, the last part of a multipart message, in this case
#                    # the HTML message, is best and preferred.
##                    if core_obj.send_pref in ('text', 'mixed', 'alternative'):
##                        body_text = body.get('text', u'<Empty Message>')
##                        body_text = tools.ustr(body_text)
##                        text_part.attach(MIMEText(body_text.encode("utf-8"), _charset='UTF-8'))
##                    if core_obj.send_pref in ('html', 'mixed', 'alternative'):
#                    html_body = body.get('html', u'')
#                    if len(html_body) == 0 or html_body == u'':
#                        html_body = body.get('text', u'<p>&lt;Empty Message&gt;</p>').replace('\n', '<br/>').replace('\r', '<br/>')
#                    html_body = tools.ustr(html_body)
#                    text_part.attach(MIMEText(html_body.encode("utf-8"), _subtype='html', _charset='UTF-8'))
#
#                    #Now add attachments if any, wrapping into a container multipart/mixed if needed
#                    if payload:
#                        for file in payload:
#                            part = MIMEBase('application', "octet-stream")
#                            part.set_payload(base64.decodestring(payload[file]))
#                            part.add_header('Content-Disposition', 'attachment; filename="%s"' % file)
#                            Encoders.encode_base64(part)
#                            payload_part.attach(part)
#                except Exception, error:
#                    logger.notifyChannel(_("Email Template"), netsvc.LOG_ERROR, _("Mail from Account %s failed. Probable Reason:MIME Error\nDescription: %s") % (id, error))
#                    return {'error_msg': _("Server Send Error\nDescription: %s")%error}
#                try:
#                    serv.sendmail(payload_part['From'], addresses_l['all-recipients'], payload_part.as_string())
#                except Exception, error:
#                    logging.getLogger('email_template').error(_("Mail from Account %s failed. Probable Reason: Server Send Error\n Description: %s"), id, error, exc_info=True)
#                    return {'error_msg': _("Server Send Error\nDescription: %s")%error}
#                #The mail sending is complete
#                serv.close()
#                logger.notifyChannel(_("Email Template"), netsvc.LOG_INFO, _("Mail from Account %s successfully Sent.") % (id))
#                return True
#            else:
#                logger.notifyChannel(_("Email Template"), netsvc.LOG_ERROR, _("Mail from Account %s failed. Probable Reason:Account not approved") % id)
#                return {'nodestroy':True,'error_msg': _("Mail from Account %s failed. Probable Reason:Account not approved")% id}
#
#    def extracttime(self, time_as_string):
#        """
#        TODO: DOC THis
#        """
#        logger = netsvc.Logger()
#        #The standard email dates are of format similar to:
#        #Thu, 8 Oct 2009 09:35:42 +0200
#        date_as_date = False
#        convertor = {'+':1, '-':-1}
#        try:
#            time_as_string = time_as_string.replace(',', '')
#            date_list = time_as_string.split(' ')
#            date_temp_str = ' '.join(date_list[1:5])
#            if len(date_list) >= 6:
#                sign = convertor.get(date_list[5][0], False)
#            else:
#                sign = False
#            try:
#                dt = datetime.datetime.strptime(
#                                            date_temp_str,
#                                            "%d %b %Y %H:%M:%S")
#            except:
#                try:
#                    dt = datetime.datetime.strptime(
#                                            date_temp_str,
#                                            "%d %b %Y %H:%M")
#                except:
#                    return False
#            if sign:
#                try:
#                    offset = datetime.timedelta(
#                                hours=sign * int(
#                                             date_list[5][1:3]
#                                                ),
#                                             minutes=sign * int(
#                                                            date_list[5][3:5]
#                                                                )
#                                                )
#                except Exception, e2:
#                    """Looks like UT or GMT, just forget decoding"""
#                    return False
#            else:
#                offset = datetime.timedelta(hours=0)
#            dt = dt + offset
#            date_as_date = dt.strftime('%Y-%m-%d %H:%M:%S')
#        except Exception, e:
#            logger.notifyChannel(
#                    _("Email Template"),
#                    netsvc.LOG_WARNING,
#                    _(
#                      "Datetime Extraction failed.Date:%s \
#                      \tError:%s") % (
#                                    time_as_string,
#                                    e)
#                      )
#        return date_as_date
#
#    def send_receive(self, cr, uid, ids, context=None):
#        for id in ids:
#            ctx = context.copy()
#            ctx['filters'] = [('account_id', '=', id)]
#            self.pool.get('email.message').send_all_mail(cr, uid, [], context=ctx)
#        return True
#
#    def decode_header_text(self, text):
#        """ Decode internationalized headers RFC2822.
#            To, CC, BCC, Subject fields can contain
#            text slices with different encodes, like:
#                =?iso-8859-1?Q?Enric_Mart=ED?= <enricmarti@company.com>,
#                =?Windows-1252?Q?David_G=F3mez?= <david@company.com>
#            Sometimes they include extra " character at the beginning/
#            end of the contact name, like:
#                "=?iso-8859-1?Q?Enric_Mart=ED?=" <enricmarti@company.com>
#            and decode_header() does not work well, so we use regular
#            expressions (?=   ? ?   ?=) to split the text slices
#        """
#        if not text:
#            return text
#        p = re.compile("(=\?.*?\?.\?.*?\?=)")
#        text2 = ''
#        try:
#            for t2 in p.split(text):
#                text2 += ''.join(
#                            [s.decode(
#                                      t or 'ascii'
#                                    ) for (s, t) in decode_header(t2)]
#                                ).encode('utf-8')
#        except:
#            return text
#        return text2

email_smtp_server()

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
        'date': fields.datetime('Date', readonly=True),
        'user_id': fields.many2one('res.users', 'User Responsible', readonly=True),
        'message': fields.text('Description', readonly=True),
        'email_from': fields.char('From', size=128, help="Email From", readonly=True),
        'email_to': fields.char('To', help="Email Recipients", size=256, readonly=True),
        'email_cc': fields.char('Cc', help="Carbon Copy Email Recipients", size=256, readonly=True),
        'email_bcc': fields.char('Bcc', help='Blind Carbon Copy Email Recipients', size=256, readonly=True),
        'message_id': fields.char('Message Id', size=1024, readonly=True, help="Message Id on Email.", select=True),
        'references': fields.text('References', readonly=True, help="References emails."),
        'partner_id': fields.many2one('res.partner', 'Partner', required=False),
        'attachment_ids': fields.many2many('ir.attachment', 'message_attachment_rel', 'message_id', 'attachment_id', 'Attachments', readonly=True),
        'display_text': fields.function(_get_display_text, method=True, type='text', size="512", string='Display Text'),
        'reply_to':fields.char('Reply-To', size=250, readonly=True),
        'account_id' :fields.many2one('email.smtp_server', 'User account', readonly=True),
        'sub_type': fields.char('Sub Type', size=32, readonly=True),
        'x_headers': fields.char('x_headers',size=256, readonly=True),
        'priority':fields.integer('Priority', readonly=True),
        'debug':fields.boolean('Debug', readonly=True),
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
                        ('waiting', 'Waiting'),
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
            self.email_send(cursor, user, context=context)
        except Exception, e:
            LOGGER.notifyChannel(
                                 "Email Template",
                                 netsvc.LOG_ERROR,
                                 _("Error sending mail: %s") % e)

    def email_send(self, cr, uid, ids=None, context=None):
        if ids is None:
            ids = []
        if context is None:
            context = {}
        attachment_obj = self.pool.get('ir.attachment')
        account_obj = self.pool.get('email.smtp_server')
        if not ids:
            filters = [('folder', '=', 'outbox'), ('state', '!=', 'sending')]
            if 'filters' in context:
                filters.extend(context['filters'])
            ids = self.search(cr, uid, filters, context=context)
            self.write(cr, uid, ids, {'state':'sending', 'folder':'sent'}, context)
        for message in self.browse(cr, uid, ids, context):
            try:
                attachments = []
                for attach in message.attachment_ids:
                    attachments.append((attach.datas_fname ,attach.datas))
                smtp_account = False
                if message.account_id:
                    account_id = smtp_account
                else:
                    smtp_ids = account_obj.search(cr, uid, [('default','=',True)])
                    if smtp_ids:
                        smtp_account = account_obj.browse(cr, uid, smtp_ids, context)[0]
                tools.email_send(message.email_from, message.email_to, message.name, message.message, email_cc=message.email_cc,
                        email_bcc=message.email_bcc, reply_to=message.reply_to, attach=attachments, openobject_id=message.message_id,
                        subtype=message.sub_type, x_headers=message.x_headers, priority=message.priority, debug=message.debug,
                        smtp_email_from=smtp_account and smtp_account.email_id or None, smtp_server=smtp_account and smtp_account.smtpserver or None,
                        smtp_port=smtp_account and smtp_account.smtpport or None, ssl=smtp_account and smtp_account.smtpssl or False,
                        smtp_user=smtp_account and smtp_account.smtpuname or None, smtp_password=smtp_account and smtp_account.smtppass or None)
            except Exception, error:
                logger = netsvc.Logger()
                logger.notifyChannel("email-template", netsvc.LOG_ERROR, _("Sending of Mail %s failed. Probable Reason:Could not login to server\nError: %s") % (message.id, error))
        return True

#    def send_all_mail(self, cr, uid, ids=None, context=None):
#        if ids is None:
#            ids = []
#        if context is None:
#            context = {}
#        filters = [('folder', '=', 'outbox'), ('state', '!=', 'sending')]
#        if 'filters' in context.keys():
#            for each_filter in context['filters']:
#                filters.append(each_filter)
#        ids = self.search(cr, uid, filters, context=context)
#        self.write(cr, uid, ids, {'state':'sending'}, context)
#        self.send_this_mail(cr, uid, ids, context)
#        return True
#
#    def send_this_mail(self, cr, uid, ids=None, context=None):
#        #previous method to send email (link with email account can be found at the revision 4172 and below
#        result = True
#        attachment_pool = self.pool.get('ir.attachment')
#        for id in (ids or []):
#            try:
#                account_obj = self.pool.get('email.smtp_server')
#                values = self.read(cr, uid, id, [], context)
#                payload = {}
#                if values['attachments_ids']:
#                    for attid in values['attachments_ids']:
#                        attachment = attachment_pool.browse(cr, uid, attid, context)#,['datas_fname','datas'])
#                        payload[attachment.datas_fname] = attachment.datas
#                result = account_obj.send_email(cr, uid,
#                              [values['account_id'][0]],
#                              {'To':values.get('email_to') or u'',
#                               'CC':values.get('email_cc') or u'',
#                               'BCC':values.get('email_bcc') or u'',
#                               'Reply-To':values.get('reply_to') or u''},
#                              values['subject'] or u'',
#                              {'text':values.get('body_text') or u'', 'html':values.get('body_html') or u''},
#                              payload=payload,
#                              message_id=values['message_id'],
#                              context=context)
#                if result == True:
#                    account = account_obj.browse(cr, uid, values['account_id'][0], context=context)
#                    if account.auto_delete:
#                        self.write(cr, uid, id, {'folder': 'trash'}, context=context)
#                        self.unlink(cr, uid, [id], context=context)
#                        # Remove attachments for this mail
#                        attachment_pool.unlink(cr, uid, values['attachments_ids'], context=context)
#                    else:
#                        self.write(cr, uid, id, {'folder':'sent', 'state':'na', 'date_mail':time.strftime("%Y-%m-%d %H:%M:%S")}, context)
#                else:
#                    error = result['error_msg']
#
#            except Exception, error:
#                logger = netsvc.Logger()
#                logger.notifyChannel("email-template", netsvc.LOG_ERROR, _("Sending of Mail %s failed. Probable Reason:Could not login to server\nError: %s") % (id, error))
#            self.write(cr, uid, id, {'state':'na'}, context)
#        return result

email_message()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
