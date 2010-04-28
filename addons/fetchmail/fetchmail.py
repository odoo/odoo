#!/usr/bin/env python
#-*- coding:utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution    
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    mga@tinyerp.com
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
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import os
import re
import time

import email
import binascii
import mimetypes

from imaplib import IMAP4
from imaplib import IMAP4_SSL   

from poplib import POP3
from poplib import POP3_SSL

from email.header import Header
from email.header import decode_header

import netsvc
from osv import osv
from osv import fields
from tools.translate import _

logger = netsvc.Logger()

def html2plaintext(html, body_id=None, encoding='utf-8'):
    ## (c) Fry-IT, www.fry-it.com, 2007
    ## <peter@fry-it.com>
    ## download here: http://www.peterbe.com/plog/html2plaintext

    """ from an HTML text, convert the HTML to plain text.
    If @body_id is provided then this is the tag where the
    body (not necessarily <body>) starts.
    """
    try:
        from BeautifulSoup import BeautifulSoup, SoupStrainer, Comment
    except:
        return html

    urls = []
    if body_id is not None:
        strainer = SoupStrainer(id=body_id)
    else:
        strainer = SoupStrainer('body')

    soup = BeautifulSoup(html, parseOnlyThese=strainer, fromEncoding=encoding)
    for link in soup.findAll('a'):
        title = link.renderContents()
        for url in [x[1] for x in link.attrs if x[0]=='href']:
            urls.append(dict(url=url, tag=str(link), title=title))

    html = soup.__str__()

    url_index = []
    i = 0
    for d in urls:
        if d['title'] == d['url'] or 'http://'+d['title'] == d['url']:
            html = html.replace(d['tag'], d['url'])
        else:
            i += 1
            html = html.replace(d['tag'], '%s [%s]' % (d['title'], i))
            url_index.append(d['url'])

    html = html.replace('<strong>','*').replace('</strong>','*')
    html = html.replace('<b>','*').replace('</b>','*')
    html = html.replace('<h3>','*').replace('</h3>','*')
    html = html.replace('<h2>','**').replace('</h2>','**')
    html = html.replace('<h1>','**').replace('</h1>','**')
    html = html.replace('<em>','/').replace('</em>','/')

    # the only line breaks we respect is those of ending tags and
    # breaks

    html = html.replace('\n',' ')
    html = html.replace('<br>', '\n')
    html = html.replace('<tr>', '\n')
    html = html.replace('</p>', '\n\n')
    html = re.sub('<br\s*/>', '\n', html)
    html = html.replace(' ' * 2, ' ')

    # for all other tags we failed to clean up, just remove then and
    # complain about them on the stderr
    def desperate_fixer(g):
        #print >>sys.stderr, "failed to clean up %s" % str(g.group())
        return ' '

    html = re.sub('<.*?>', desperate_fixer, html)

    # lstrip all lines
    html = '\n'.join([x.lstrip() for x in html.splitlines()])

    for i, url in enumerate(url_index):
        if i == 0:
            html += '\n\n'
        html += '[%s] %s\n' % (i+1, url)
    return html
    
class email_server(osv.osv):
    
    _name = 'email.server'
    _description = "POP/IMAP Server"
    
    _columns = {
        'name':fields.char('Name', size=256, required=True, readonly=False),
        'active':fields.boolean('Active', required=False),
        'state':fields.selection([
            ('draft','Not Confirme'),
            ('wating','Waiting for Verification'),
            ('done','Confirmed'),
        ],'State', select=True, readonly=True),
        'server' : fields.char('Server', size=256, required=True, readonly=True, states={'draft':[('readonly',False)]}),
        'port' : fields.integer('Port', required=True, readonly=True, states={'draft':[('readonly',False)]}),
        'type':fields.selection([
            ('pop','POP Server'),
            ('imap','IMAP Server'),
        ],'State', select=True, readonly=False),
        'is_ssl':fields.boolean('SSL ?', required=False),
        'attach':fields.boolean('Add Attachments ?', required=False),
        'date': fields.date('Date', readonly=True, states={'draft':[('readonly',False)]}),
        'user' : fields.char('User Name', size=256, required=True, readonly=True, states={'draft':[('readonly',False)]}),
        'password' : fields.char('Password', size=1024, invisible=True, required=True, readonly=True, states={'draft':[('readonly',False)]}),
        'note': fields.text('Description'),
        'action_id':fields.many2one('ir.actions.server', 'Reply Email', required=False, domain="[('state','=','email')]"),
        'object_id': fields.many2one('ir.model',"Model", required=True),
        'priority': fields.integer('Server Priority', readonly=True, states={'draft':[('readonly',False)]}, help="Priority between 0 to 10, select define the order of Processing"),
        'user_id':fields.many2one('res.users', 'User', required=False),
    }
    _defaults = {
        'state': lambda *a: "draft",
        'active': lambda *a: True,
        'priority': lambda *a: 5,
        'date': lambda *a: time.strftime('%Y-%m-%d'),
        'user_id': lambda self, cr, uid, ctx: uid,
    }
    
    def check_duplicate(self, cr, uid, ids):
        vals = self.read(cr, uid, ids, ['user', 'password'])[0]
        cr.execute("select count(id) from email_server where user='%s' and password='%s'" % (vals['user'], vals['password']))
        res = cr.fetchone()
        if res:
            if res[0] > 1:
                return False
        return True 

    _constraints = [
        (check_duplicate, 'Warning! Can\'t have duplicate server configuration!', ['user', 'password'])
    ]
    
    def onchange_server_type(self, cr, uid, ids, server_type=False, ssl=False):
        port = 0
        if server_type == 'pop':
            port = ssl and 995 or 110
        elif server_type == 'imap':
            port = ssl and 993 or 143
        
        return {'value':{'port':port}}
    
    def _process_email(self, cr, uid, server, message, context={}):
        context.update({
            'server_id':server.id
        })
        history_pool = self.pool.get('mail.server.history')
        msg_txt = email.message_from_string(message)
        message_id = msg_txt.get('Message-ID', False)
        
        msg = {}
        if not message_id:
            return False
        
        fields = msg_txt.keys()
        
        msg['id'] = message_id
        msg['message-id'] = message_id
        
        if 'Subject' in fields:
            msg['subject'] = msg_txt.get('Subject')
        
        if 'Content-Type' in fields:
            msg['content-type'] = msg_txt.get('Content-Type')
        
        if 'From' in fields:
            msg['from'] = msg_txt.get('From')
        
        if 'Delivered-To' in fields:
            msg['to'] = msg_txt.get('Delivered-To')
        
        if 'Cc' in fields:
            msg['cc'] = msg_txt.get('Cc')
        
        if 'Reply-To' in fields:
            msg['reply'] = msg_txt.get('Reply-To')
        
        if 'Date' in fields:
            msg['date'] = msg_txt.get('Date')
        
        if 'Content-Transfer-Encoding' in fields:
            msg['encoding'] = msg_txt.get('Content-Transfer-Encoding')
        
        if 'References' in fields:
            msg['references'] = msg_txt.get('References')

        if 'X-openerp-caseid' in fields:
            msg['caseid'] = msg_txt.get('X-openerp-caseid')
        
        if 'X-Priority' in fields:
            msg['priority'] = msg_txt.get('X-priority', '3 (Normal)').split(' ')[0]
        
        if not msg_txt.is_multipart() or 'text/plain' in msg.get('content-type', None):
            msg['body'] = msg_txt.get_payload(decode=True)
        
        attachents = {}
        if msg_txt.is_multipart() or 'multipart/alternative' in msg.get('content-type', None):
            body = ""
            counter = 1
            for part in msg_txt.walk():
                if part.get_content_maintype() == 'multipart':
                    continue
                
                if part.get_content_maintype()=='text':
                    content = part.get_payload(decode=True)
                    if part.get_content_subtype() == 'html':
                        body = html2plaintext(content)
                    elif part.get_content_subtype() == 'plain':
                        body = content
                    
                    filename = part.get_filename()
                    if filename :
                        attachents[filename] = part.get_payload(decode=True)
                    
                elif part.get_content_maintype()=='application' or part.get_content_maintype()=='image' or part.get_content_maintype()=='text':
                    filename = part.get_filename();
                    if filename :
                        attachents[filename] = part.get_payload(decode=True)
                    else:
                        body += part.get_payload(decode=True)

            msg['body'] = body
            msg['attachments'] = attachents

        res_id = False
        if msg.get('references', False):
            id = False
            ref = msg.get('references')
            if '\r\n' in ref:
                ref = msg.get('references').split('\r\n')
            else:
                ref = msg.get('references').split(' ')
                
            if ref:
                hids = history_pool.search(cr, uid, [('name','=',ref[0].strip())])
                if hids:
                    id = hids[0]
                    history = history_pool.browse(cr, uid, id)
                    model_pool = self.pool.get(server.object_id.model)
                    context.update({
                        'references_id':ref[0]
                    })
                    vals = {
                    
                    }
                    if hasattr(model_pool, 'message_update'):
                        model_pool.message_update(cr, uid, [history.res_id], vals, msg, context=context)
                    else:
                        logger.notifyChannel('imap', netsvc.LOG_WARNING, 'method def message_update is not define in model %s' % (model_pool._name))
                        return False
            res_id = id
        else:
            model_pool = self.pool.get(server.object_id.model)
            if hasattr(model_pool, 'message_new'):
                res_id = model_pool.message_new(cr, uid, msg, context)
            else:
                logger.notifyChannel('imap', netsvc.LOG_WARNING, 'method def message_new is not define in model %s' % (model_pool._name))
                return False
            
            if server.attach:
                for attactment in attachents or []:
                    data_attach = {
                        'name': attactment,
                        'datas':binascii.b2a_base64(str(attachents.get(attactment))),
                        'datas_fname': attactment,
                        'description': 'Mail attachment',
                        'res_model': server.object_id.model,
                        'res_id': res_id,
                    }
                    self.pool.get('ir.attachment').create(cr, uid, data_attach)
            
            if server.action_id:
                action_pool = self.pool.get('ir.actions.server')
                action_pool.run(cr, uid, [server.action_id.id], {'active_id':res_id, 'active_ids':[res_id]})
            
            res = {
                'name': message_id, 
                'res_id': res_id, 
                'server_id': server.id, 
                'note': msg.get('body', msg.get('from')),
                'ref_id':msg.get('references', msg.get('id')),
                'type':server.type
            }
            his_id = history_pool.create(cr, uid, res)
            
        return res_id

    def set_draft(self, cr, uid, ids, context={}):
        self.write(cr, uid, ids , {'state':'draft'})
        return True
        
    def button_fetch_mail(self, cr, uid, ids, context={}):
        self.fetch_mail(cr, uid, ids)
#        sendmail_thread = threading.Thread(target=self.fetch_mail, args=(cr, uid, ids))
#        sendmail_thread.start()
        return True
        
    def _fetch_mails(self, cr, uid, ids=False, context={}):
        if not ids:
            ids = self.search(cr, uid, [])
        return self.fetch_mail(cr, uid, ids, context)
    
    def fetch_mail(self, cr, uid, ids, context={}):

        fp = os.popen('ping www.google.com -c 1 -w 5',"r")
        if not fp.read():
            logger.notifyChannel('imap', netsvc.LOG_WARNING, 'lost internet connection !')

        for server in self.browse(cr, uid, ids, context):
            logger.notifyChannel('imap', netsvc.LOG_INFO, 'fetchmail start checking for new emails on %s' % (server.name))
            
            count = 0
            try:
                if server.type == 'imap':
                    imap_server = None
                    if server.is_ssl:
                        imap_server = IMAP4_SSL(server.server, int(server.port))
                    else:
                        imap_server = IMAP4(server.server, int(server.port))
                    
                    imap_server.login(server.user, server.password)
                    imap_server.select()
                    result, data = imap_server.search(None, '(UNSEEN)')
                    for num in data[0].split():
                        result, data = imap_server.fetch(num, '(RFC822)')
                        if self._process_email(cr, uid, server, data[0][1], context):
                            imap_server.store(num, '+FLAGS', '\\Seen')
                            count += 1
                    logger.notifyChannel('imap', netsvc.LOG_INFO, 'fetchmail fetch/process %s email(s) from %s' % (count, server.name))
                    
                    imap_server.close()
                    imap_server.logout()
                elif server.type == 'pop':
                    pop_server = None
                    if server.is_ssl:
                        pop_server = POP3_SSL(server.server, int(server.port))
                    else:
                        pop_server = POP3(server.server, int(server.port))
                   
                    #TODO: use this to remove only unread messages
                    #pop_server.user("recent:"+server.user)
                    pop_server.user(server.user)
                    pop_server.pass_(server.password)
                    pop_server.list()

                    (numMsgs, totalSize) = pop_server.stat()
                    for num in range(1, numMsgs + 1):
                        (header, msges, octets) = pop_server.retr(num)
                        msg = '\n'.join(msges)
                        self._process_email(cr, uid, server, msg, context)
                        pop_server.dele(num)

                    pop_server.quit()
                    
                    logger.notifyChannel('imap', netsvc.LOG_INFO, 'fetchmail fetch %s email(s) from %s' % (numMsgs, server.name))
                
                self.write(cr, uid, [server.id], {'state':'done'})
            except Exception, e:
                logger.notifyChannel(server.type, netsvc.LOG_WARNING, '%s' % (e))
                
        return True

email_server()

class mail_server_history(osv.osv):

    _name = "mail.server.history"
    _description = "Mail Server History"
    
    _columns = {
        'name': fields.char('Message Id', size=256, readonly=True, help="Message Id in Email Server.", select=True),
        'ref_id': fields.char('Referance Id', size=256, readonly=True, help="Message Id in Email Server.", select=True),
        'res_id': fields.integer("Resource ID", readonly=True, select=True),
        'server_id': fields.many2one('email.server',"Mail Server", readonly=True, select=True),
        'model_id':fields.related('server_id', 'object_id', type='many2one', relation='ir.model', string='Model', readonly=True, select=True), 
        'note': fields.text('Notes', readonly=True),
        'create_date': fields.datetime('Created Date', readonly=True),
        'type':fields.selection([
            ('pop','POP Server'),
            ('imap','IMAP Server'),
        ],'State', select=True, readonly=True),
    }
    _order = 'id desc'
    
mail_server_history()

class fetchmail_tool(osv.osv):

    _name = 'email.server.tools'
    _description = "Email Tools"
    _auto = False
    
    def to_email(self, text):
        _email = re.compile(r'.*<.*@.*\..*>', re.UNICODE)
        def record(path):
            eml = path.group()
            index = eml.index('<')
            eml = eml[index:-1].replace('<','').replace('>','')
            return eml

        bits = _email.sub(record, text)
        return bits
    
    def get_partner(self, cr, uid, from_email, context=None):
        """
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks
        @param from_email: email address based on that function will search for the correct 
        """
        
        res = {
            'partner_address_id': False,
            'partner_id': False
        }
        from_email = self.to_email(from_email)
        address_ids = self.pool.get('res.partner.address').search(cr, uid, [('email', '=', from_email)])
        if address_ids:
            address = self.pool.get('res.partner.address').browse(cr, uid, address_ids[0])
            res['partner_address_id'] = address_ids[0]
            res['partner_id'] = address.partner_id.id
        
        return res
        
fetchmail_tool()
