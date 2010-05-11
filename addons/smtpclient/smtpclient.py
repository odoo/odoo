##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import os
import sys
import bz2

import time
from datetime import datetime
from datetime import timedelta

import release
import socket

import base64
import binascii

import random
import smtplib
import mimetypes

from email import Encoders
from optparse import OptionParser
from email.Message import Message
from email.MIMEBase import MIMEBase
from email.MIMEText import MIMEText
from email.MIMEMultipart import MIMEMultipart
from email.Utils import COMMASPACE, formatdate

import netsvc
import pooler
import tools

from osv import fields
from osv import osv
from tools.translate import _

error_msg = {
    'not_active' : "Please activate Email Server, without activating you can not send Email(s).",
    'server_stop' : 'Please start Email Server, without starting  you can not send Email(s).',
    'server_not_confirm' : 'Please Verify Email Server, without verifying you can not send Email(s).'
}

logger = netsvc.Logger()

class smtpclient(osv.osv):

    _name = 'email.smtpclient'
    _description = 'Email Client'

    _columns = {
        'name' : fields.char('Server Name', size=256, required=True),
        'from_email' : fields.char('Email From', size=256),
        'email':fields.char('Email Address', size=256, required=True, readonly=True, states={'new':[('readonly',False)]}),
        'cc_to':fields.char('Send copy to', size=256, readonly=True, states={'new':[('readonly',False)]}, help="use comma to supply multiple address. email@domain.com, email2@domain.com"),
        'bcc_to':fields.char('Send blind copy to', size=256, readonly=True, states={'new':[('readonly',False)]}, help="use comma to supply multiple address. email@domain.com, email2@domain.com"),
        'user' : fields.char('User Name', size=256, readonly=True, states={'new':[('readonly',False)]}),
        'password' : fields.char('Password', size=1024, invisible=True, readonly=True, states={'new':[('readonly',False)]}),
        'server' : fields.char('SMTP Server', size=256, required=True, readonly=True, states={'new':[('readonly',False)]}),
        'auth' : fields.boolean("Use Auth", readonly=True, states={'new':[('readonly',False)]}),
        'port' : fields.char('SMTP Port', size=256, required=True, readonly=True, states={'new':[('readonly',False)]}),
        'ssl' : fields.boolean("Use SSL?", readonly=True, states={'new':[('readonly',False)]}),
        'users_id': fields.many2many('res.users', 'res_smtpserver_group_rel', 'sid', 'uid', 'Users Allowed'),
        'state': fields.selection([
            ('new','Not Verified'),
            ('waiting','Waiting for Verification'),
            ('confirm','Verified'),
        ],'Server Status', select=True, readonly=True),
        'auth_type':fields.selection([('gmail','Google Server'), ('yahoo','Yahoo!!! Server'), ('unknown','Other Mail Servers')], string="Server Type", readonly=True, states={'new':[('readonly',False)]}),
        'active' : fields.boolean("Active"),
        'date_create': fields.date('Date Create', required=True, readonly=True),
        'test_email' : fields.text('Test Message', translate=True),
        'body' : fields.text('Message', translate=True, help="The message text that will be send along with the email which is send through this server"),
        'verify_email' : fields.text('Verify Message', translate=True, readonly=True, states={'new':[('readonly',False)]}),
        'code' : fields.char('Verification Code', size=1024),
        'type' : fields.selection([("default", "Default"),("account", "Account"),("sale","Sale"),("stock","Stock")], "Server Type",required=True),
        'history_line': fields.one2many('email.smtpclient.history', 'server_id', 'History'),
        'server_statistics': fields.one2many('report.smtp.server', 'server_id', 'Statistics'),
        'delete_queue': fields.selection([
            ('never','Never Delete Message'),
            ('content','Delete Content After'),
            ('all','Clear All After'),
            ('after_send','Delete when Email Sent'),
        ],'Queue Option', select=True),
        'priority': fields.integer('Server Priority', readonly=True, states={'new':[('readonly',False)]}, help="Priority between 0 to 10, will be used to define the MTA process priotiry"),
        'header_ids':fields.one2many('email.headers', 'server_id', 'Default Headers'),
        'disclaimers': fields.text('Disclaimers'),
        'process_id': fields.many2one('ir.cron', 'MTA Process', readonly=True, help="Mail Transport Agent Process"),
        'pstate': fields.selection([
            ('running','Running'),
            ('stop','Stop'),
        ],'Server Statue', select=True, readonly=True),
        'delete_queue_period': fields.integer('Delete after', help="delete emails/contents from email queue after specified no of days"),
    }

    def _get_users(self, cr, uid, context={}):
        return self.pool.get('res.users').search(cr, uid, [])

    _defaults = {
        'date_create': lambda *a: time.strftime('%Y-%m-%d'),
        'state': lambda *a: 'new',
        'type': lambda *a: 'default',
        'port': lambda *a: '25',
        'pstate':lambda *a: 'stop',
        'priority': lambda *a: 5,
        'delete_queue_period': lambda *a: 30,
        'auth': lambda *a: True,
        'active': lambda *a: True,
        'delete_queue': lambda *a: 'never',
        'users_id': _get_users,
        'verify_email': lambda *a: _("Verification Message. This is the code\n\n__code__\n\nyou must copy in the OpenERP Email Server (Verify Server wizard).\n\nCreated by user __user__"),
    }

    server = {}
    smtpServer = {}

    def create(self, cr, user, vals, context={}):
        if vals.get('password', False) != False:
            vals['password'] = base64.b64encode(vals.get('password'))

        res_id = super(smtpclient, self).create(cr, user, vals, context)
        return res_id

    def write(self, cr, user, ids, vals, context=None):
        flag = False
        if vals.get('password', False) != False:
            for pass_char in vals.get('password'):
                if pass_char != '*':
                    flag= True
                    break

            if flag:
                vals['password'] = base64.b64encode(vals.get('password'))
            else:
                del vals['password']

        res = super(smtpclient, self).write(cr, user, ids, vals, context)
        return res

    def read(self,cr, uid, ids, fields=None, context=None, load='_classic_read'):
        def override_password(o):
            if len(o) > 0:
                for field in o[0]:
                    if field == 'password':
                        o[0][field] = '********'
            return o

        result = super(smtpclient, self).read(cr, uid, ids, fields, context, load)
        result = override_password(result)
        return result

    def change_servertype(self, cr, uid, ids, server):
        if server == 'gmail':
            return {'value':{'server':'smtp.gmail.com', 'port':'25', 'ssl':True, 'auth':True}}
        elif server== 'yahoo':
            return {'value':{'server':'smtp.mail.yahoo.co.in', 'ssl':False, 'port':'587', 'auth':True}}
        else:
            return {'value':{'server':'localhost', 'port':'25', 'ssl':False, 'auth':False}}

    def change_email(self, cr, uid, ids, email):
        email_from = self.pool.get('res.users').browse(cr, uid, uid).name
        if len(email) > 0 and email.find('@') > -1 and email.index('@') > 0:
            user = email[0:email.index('@')]
            return {'value':{'user':user, 'from_email':email_from+' <'+email+'>'}}
        else:
            return {'value':{'user':email, 'from_email':email_from+' <'+email+'>'}}

    def check_permissions(self, cr, uid, ids):
        if uid == 1:
            return True
        cr.execute('select * from res_smtpserver_group_rel where sid=%s and uid=%s' % (ids[0], uid))
        data = cr.fetchall()
        if len(data) <= 0:
            return False

        return True

    def gen_private_key(self, cr, uid, ids):
        new_key = []
        for i in time.strftime('%Y-%m-%d %H:%M:%S'):
            ky = i
            if ky in (' ', '-', ':'):
                keys = random.random()
                key = str(keys).split('.')[1]
                ky = key

            new_key.append(ky)
        new_key.sort()
        key = ''.join(new_key)
        return key


    def _set_error(self, cr, uid, server_id, context={}):
        server_obj = self.browse(cr, uid, server_id)
        if not server_obj.active:
            return 'not_active'
        if server_obj.pstate == 'stop' :
            return 'server_stop'
        if server_obj.state != 'confirm':
            return 'server_not_confirm'
        return True

    def test_verify_email(self, cr, uid, ids, toemail, test=False, code=False):

        serverid = ids[0]
        self.open_connection(cr, uid, ids, serverid)

        key = False
        if test and self.server[serverid]['state'] == 'confirm':
            body = self.server[serverid]['test_email'] or ''
        else:
            body = self.server[serverid]['verify_email'] or ''
            #ignore the code
            key = self.gen_private_key(cr, uid, ids)
            #md5(time.strftime('%Y-%m-%d %H:%M:%S') + toemail).hexdigest();

            body = body.replace("__code__", key)

        user = pooler.get_pool(cr.dbname).get('res.users').browse(cr, uid, [uid])[0]
        body = body.replace("__user__", user.name)

        if len(body.strip()) <= 0:
            raise osv.except_osv(_('Message Error!'), _('Please configure Email Server Messages [Verification / Test]'))

        try:
            msg = MIMEText(body.encode('utf8') or '',_subtype='plain',_charset='utf-8')
        except:
            msg = MIMEText(body or '',_subtype='plain',_charset='utf-8')

        if not test and not self.server[serverid]['state'] == 'confirm':
            msg['Subject'] = _('OpenERP SMTP server Email Registration Code!')
        else:
            msg['Subject'] = _('OpenERP Test Email!')

        msg['To'] = toemail
        if context.get('email_from', self.server[serverid]['from_email']):
            msg['From'] = context.get('email_from', self.server[serverid]['from_email'])
        elif tools.config['email_from']:
            msg['From'] = tools.config['email_from']
        else:
            raise osv.except_osv(_('Error'), _("Please specify server option --email-from !"))

        message = msg.as_string()

        if self.server[serverid]['disclaimers']:
            body = body + "\n" + self.server[serverid]['disclaimers']

        queue = pooler.get_pool(cr.dbname).get('email.smtpclient.queue')
        queue.create(cr, uid, {
            'to':toemail,
            'server_id':serverid,
            'name':msg['Subject'],
            'body':body,
            'serialized_message':message,
            'priority':1,
            'type':'system'
        })

        if self.server[serverid]['state'] != 'confirm':
            self.write(cr, uid, ids, {'state':'waiting', 'code':key})

        return True

    def getpassword(self, cr, uid, ids):
        data = {}
        cr.execute("select * from email_smtpclient where id = %s" , (str(ids[0]),))
        data = cr.dictfetchall()
        return data

    def open_connection(self, cr, uid, ids, serverid=False, permission=True):
        if serverid:
            self.server[serverid] = self.getpassword(cr, uid, [serverid])[0]
        else:
            raise osv.except_osv(_('Read Error!'), _('Unable to read Server Settings'))

        if permission:
            if not self.check_permissions(cr, uid, [serverid]):
                raise osv.except_osv(_('Permission Error!'), _('You have no permission to access SMTP Server : %s ') % (self.server[serverid]['name'],) )

        if self.server[serverid]:
            try:
                self.smtpServer[serverid] = smtplib.SMTP()
                self.smtpServer[serverid].debuglevel = 0
                self.smtpServer[serverid].connect(str(self.server[serverid]['server']),str(self.server[serverid]['port']))

                if self.server[serverid]['ssl']:
                    self.smtpServer[serverid].ehlo()
                    self.smtpServer[serverid].starttls()
                    self.smtpServer[serverid].ehlo()

                if self.server[serverid]['auth']:
                    password = self.server[serverid]['password']
                    try:
                        password = base64.b64decode(password)
                    except:
                        pass
                    self.smtpServer[serverid].login(str(self.server[serverid]['user']), password)

            except Exception, e:
                logger.notifyChannel('imap', netsvc.LOG_WARNING, e)

        return True

    def selectAddress(self, cr, uid, partner=None, contact=None, ):
        email = 'none@none.com'
        if partner is None and contact is None:
            return 'none@none.com'

        if partner is not None and contact is None:
            pool = self.pool.get('res.partner')
            data = pool.read(cr, uid, [partner])[0]
            if data:
                contact = data['address']

        if contact is not None:
            pool = self.pool.get('res.partner.address')
            data = pool.read(cr, uid, contact)[0]
            email = data['email']

        return email

    def select(self, cr, uid, type):
        pool = self.pool.get('email.smtpclient')
        ids = pool.search(cr, uid, [('type','=',type)], context=False)
        if not ids:
            ids = pool.search(cr, uid, [('type','=','default')], context=False)

        if not ids:
            return False

        return ids[0]

    # Reports is a list of tuples,where first arguement of tuple is the name of the report,second is the list of ids of the object
    def send_email(self, cr, uid, server_id, emailto, subject, body='', attachments=[], reports=[], ir_attach=[], charset='utf-8', headers={}, context={}):

        if not emailto:
            raise osv.except_osv(_('SMTP Data Error !'), _('Email TO Address not Defined !'))

        def createReport(cr, uid, report, ids, name=False):
            files = []
            for id in ids:
                try:
                    service = netsvc.LocalService(report)
                    (result, format) = service.create(cr, uid, [id], {}, {})
                    if not name:
                        report_file = '/tmp/reports'+ str(id) + '.pdf'
                    else:
                        report_file = name

                    fp = open(report_file,'wb+')
                    fp.write(result);
                    fp.close();
                    files += [report_file]
                except Exception,e:
                    continue
            return files

        smtp_server = self.browse(cr, uid, server_id)
        if smtp_server.state != 'confirm':
            raise osv.except_osv(_('SMTP Server Error !'), _('Server is not Verified, Please Verify the Server !'))

        if not subject:
            subject = "OpenERP Email: [Unknown Subject]"

        try:
            subject = subject.encode(charset)
        except:
            subject = subject.decode()

        #attachment from Reports
        for rpt in reports:
            if len(rpt) == 3:
                rpt_file = createReport(cr, uid, rpt[0], rpt[1], rpt[2])
            elif len(rpt) == 2:
                rpt_file = createReport(cr, uid, rpt[0], rpt[1])
            attachments += rpt_file

        if isinstance(emailto, str) or isinstance(emailto, unicode):
            emailto = [emailto]

        ir_pool = self.pool.get('ir.attachment')

        for to in emailto:
            msg = MIMEMultipart()
            msg['Subject'] = tools.ustr(subject)
            msg['To'] =  to
            print "::context.get('email_from', smtp_server.from_email):::",context.get('email_from', smtp_server.from_email)
            print "::TOOOLL::",tools.config['email_from']
            if context.get('email_from', smtp_server.from_email):
                msg['From'] = context.get('email_from', smtp_server.from_email)
            elif tools.config['email_from']:
                msg['From'] = tools.config['email_from']
            else:
                raise osv.except_osv(_('Error'), _("Please specify server option --email-from !"))
            print "::<ES::",msg['From']
            if body == False:
                body = ''

            if smtp_server.disclaimers:
                body = body + "\n" + smtp_server.disclaimers

            try:
                msg.attach(MIMEText(body.encode(charset) or '', _charset=charset, _subtype="html"))
            except:
                msg.attach(MIMEText(body or '', _charset=charset, _subtype="html"))

            #add custom headers to email
            for hk in headers.keys():
                msg[hk] = headers[hk]

            for hk in smtp_server.header_ids:
                msg[hk.key] = hk.value

            context_headers = context.get('headers', [])
            for hk in context_headers:
                msg[hk] = context_headers[hk]

            # Add OpenERP Server information
            msg['X-Generated-By'] = 'OpenERP (http://www.openerp.com)'
            msg['X-OpenERP-Server-Host'] = socket.gethostname()
            msg['X-OpenERP-Server-Version'] = release.version
            msg['Message-Id'] = "<%s-openerp-@%s>" % (time.time(), socket.gethostname())

            if smtp_server.cc_to:
                msg['Cc'] = smtp_server.cc_to

            if smtp_server.bcc_to:
                msg['Bcc'] = smtp_server.bcc_to

            #attach files from disc
            for file in attachments:
                part = MIMEBase('application', "octet-stream")
                part.set_payload(open(file,"rb").read())
                Encoders.encode_base64(part)
                part.add_header('Content-Disposition', 'attachment; filename="%s"' % os.path.basename(file))
                msg.attach(part)

            #attach files from ir_attachments
            for ath in ir_pool.browse(cr, uid, ir_attach):
                part = MIMEBase('application', "octet-stream")
                datas = base64.decodestring(ath.datas)
                part.set_payload(datas)
                Encoders.encode_base64(part)
                part.add_header('Content-Disposition', 'attachment; filename="%s"' %(ath.name))
                msg.attach(part)

            message = msg.as_string()
            data = {
                'to':to,
                'server_id':server_id,
                'cc':smtp_server.cc_to or False,
                'bcc':smtp_server.bcc_to or False,
                'name':subject,
                'body':body,
                'serialized_message':message,
                'priority':smtp_server.priority,
            }
            self.create_queue_enrty(cr, uid, data, context)

        return True

    def create_queue_enrty(self, cr, uid, data, context={}):
        queue = pooler.get_pool(cr.dbname).get('email.smtpclient.queue')
        return queue.create(cr, uid, data, context)

    def _check_history(self, cr, uid, ids=False, context={}):
        result = True
        server = self.pool.get('email.smtpclient')
        queue = self.pool.get('email.smtpclient.queue')
        sids = self.search(cr, uid, [])
        for server in self.browse(cr, uid, sids):
            if server.delete_queue == 'never':
                continue

            now = datetime.today()
            days = timedelta(days=server.delete_queue_period)
            day = now - days
            kday = day.__str__().split(' ')[0]

            if server.delete_queue == 'content':
                qids = queue.search(cr, uid, [('server_id','=',server.id), ('date_create','<=',kday)])
                queue.write(cr, uid, qids, {'serialized_message':False})
                continue

            if server.delete_queue == 'all':
                qids = queue.search(cr, uid, [('server_id','=',server.id), ('date_create','<=',kday)])
                queue.unlink(cr, uid, qids)

        return result

    def _send_emails(self, cr, uid, ids, context={}):
        queue = self.pool.get('email.smtpclient.queue')
        history = self.pool.get('email.smtpclient.history')
        queue.write(cr, uid, ids, {'state':'sending'})

        error = []
        sent = []
        remove = []
        open_server = []

        for email in queue.browse(cr, uid, ids):

            if not email.server_id.id in open_server:
                open_server.append(email.server_id.id)
                self.open_connection(cr, uid, ids, email.server_id.id)

            try:
                self.smtpServer[email.server_id.id].sendmail(email.server_id.email, [email.to, email.cc, email.bcc], tools.ustr(email.serialized_message))
                message = "message sent successfully to %s from %s server" % (email.to, email.server_id.name)
                logger.notifyChannel('smtp', netsvc.LOG_INFO, message)
            except Exception, e:
                queue.write(cr, uid, [email.id], {'error':e, 'state':'error'})
                continue

            history.create(cr, uid, {
                'name':email.body,
                'user_id':uid,
                'server_id': email.server_id.id,
                'email':email.to
            })
            if email.server_id.delete_queue == 'after_send':
                remove.append(email.id)
            else:
                sent.append(email.id)

        queue.unlink(cr, uid, remove)
        queue.write(cr, uid, sent, {'state':'send'})
        return True

    def _check_queue(self, cr, uid, ids=False):
        queue = self.pool.get('email.smtpclient.queue')
        sids = []
        if not ids:
            sids = queue.search(cr, uid, [('state','not in',['send','sending']), ('type','=','system')], order="priority", limit=30)
            ids =[]
        else:
            sids = queue.search(cr, uid, [('state','not in',['send','sending']), ('server_id','in',ids)], order="priority", limit=30)

        message = ""
        if len(ids) > 1:
            message = "sending %s emails from message queuq !" % (len(ids))
            logger.notifyChannel('smtp', netsvc.LOG_INFO, message)

        result = self. _send_emails(cr, uid, sids, {})
        return result

    def set_to_draft(self, cr, uid, ids, context={}):
        self.stop_process(cr, uid, ids, context)
        self.write(cr, uid, ids, {'state':'new', 'code':False})
        return True

    def create_process(self, cr, uid, ids, context={}):
        svr = self.browse(cr, uid, ids[0])
        if not svr.process_id:
            res = {
                'name':'Process : ' + svr.name,
                'model':'email.smtpclient',
                'args': repr([ids]),
                'function':'_check_queue',
                'priority':5,
                'interval_number':1,
                'interval_type':'minutes',
                'user_id':uid,
                'numbercall':-1,
                'doall':False,
                'active':False
            }
            id = self.pool.get('ir.cron').create(cr, uid, res)
            self.write(cr, uid, ids, {'process_id':id})

        return True

    def start_process(self, cr, uid, ids, context={}):
        process = self.browse(cr, uid, ids[0], context)
        if not process.process_id or process.state != 'confirm':
            raise osv.except_osv(_('SMTP Server Error !'), _('Server is not Verified, Please Verify the Server !'))

        pid = process.process_id.id
        self.pool.get('ir.cron').write(cr, uid, [pid], {'active':True})
        self.write(cr, uid, ids, {'pstate':'running'})
        return True

    def stop_process(self, cr, uid, ids, context={}):
        pid = self.browse(cr, uid, ids[0], context).process_id.id
        self.pool.get('ir.cron').write(cr, uid, [pid], {'active':False})
        self.write(cr, uid, ids, {'pstate':'stop'})
        return True

smtpclient()

class email_headers(osv.osv):
    _name = 'email.headers'
    _description = 'Email Headers'
    _columns = {
        'server_id':fields.many2one('email.smtpclient', 'SMTP Server'),
        'key':fields.char('Header', size=64, required=True),
        'value':fields.char('Value', size=1024, required=False),
    }
email_headers()

class email_history(osv.osv):
    _name = 'email.smtpclient.history'
    _description = 'Email Client History'
    _order = 'id desc'

    _columns = {
        'name' : fields.text('Description',required=True, readonly=True),
        'date_create': fields.datetime('Date',readonly=True),
        'user_id':fields.many2one('res.users', 'Username', readonly=True, select=True),
        'server_id' : fields.many2one('email.smtpclient', 'Smtp Server', ondelete='set null', readonly=True, required=True),
        'model':fields.many2one('ir.model', 'Model', readonly=True, select=True),
        'resource_id':fields.integer('Resource ID', readonly=True),
        'email':fields.char('Email',size=64,readonly=True),
    }

    _defaults = {
        'date_create': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        'user_id': lambda obj, cr, uid, context: uid,
    }

    def create(self, cr, uid, vals, context=None):
        super(email_history,self).create(cr, uid, vals, context)
        cr.commit()
email_history()

class message_queue(osv.osv):
    _name = 'email.smtpclient.queue'
    _description = 'Email Queue'
    _order = '"to"'
    _columns = {
        'to' : fields.char('Mail to', size=1024, readonly=True, states={'draft':[('readonly',False)], 'error':[('readonly',False)]}),
        'server_id':fields.many2one('email.smtpclient', 'SMTP Server', readonly=True, states={'draft':[('readonly',False)]}),
        'cc' : fields.char('CC to', size=1024, readonly=True, states={'draft':[('readonly',False)]}),
        'bcc' : fields.char('BCC to', size=1024, readonly=True, states={'draft':[('readonly',False)]}),
        'name' : fields.char('Subject', size=1024, readonly=True, states={'draft':[('readonly',False)]}),
        'body' : fields.text('Email Text', readonly=True, states={'draft':[('readonly',False)]}),
        'serialized_message':fields.text('Message', readonly=True, states={'draft':[('readonly',False)]}),
        'state':fields.selection([
            ('draft','Queued'),
            ('sending','Waiting'),
            ('send','Sent'),
            ('error','Error'),
        ],'Message Status', select=True, readonly=True),
        'type':fields.selection([
            ('default','Default Message'),
            ('system','System Message'),
        ],'Message Type', select=True, readonly=True),
        'error':fields.text('Last Error', size=256, readonly=True, states={'draft':[('readonly',False)]}),
        'date_create': fields.datetime('Date', readonly=True),
        'priority':fields.integer('Message Priority', readonly=True),
    }
    _defaults = {
        'date_create': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        'state': lambda *a: 'draft',
        'priority': lambda *a: '10',
        'type': lambda *a: 'default',
    }
message_queue()

class report_smtp_server(osv.osv):
    _name = "report.smtp.server"
    _description = "Server Statistics"
    _auto = False
    _columns = {
        'server_id':fields.many2one('email.smtpclient','Server ID',readonly=True),
        'name': fields.char('Server',size=64,readonly=True),
        'history':fields.char('History',size=64, readonly=True),
        'no':fields.integer('Total No.',readonly=True),
    }
    def init(self, cr):
         cr.execute("""
            create or replace view report_smtp_server as (
                   select min(h.id) as id, c.id as server_id, h.name as history, h.name as name, count(h.name) as no  from email_smtpclient c inner join email_smtpclient_history h on c.id=h.server_id group by h.name, c.id
                              )
         """)

report_smtp_server()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

