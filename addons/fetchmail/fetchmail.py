# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

import logging
import time
from imaplib import IMAP4
from imaplib import IMAP4_SSL
from poplib import POP3
from poplib import POP3_SSL
try:
    import cStringIO as StringIO
except ImportError:
    import StringIO

import zipfile
import base64
import addons

import netsvc
from osv import osv, fields
import tools
from tools.translate import _

logger = logging.getLogger('fetchmail')

class fetchmail_server(osv.osv):
    """Incoming POP/IMAP mail server account"""
    _name = 'fetchmail.server'
    _description = "POP/IMAP Server"
    _order = 'priority'

    _columns = {
        'name':fields.char('Name', size=256, required=True, readonly=False),
        'active':fields.boolean('Active', required=False),
        'state':fields.selection([
            ('draft', 'Not Confirmed'),
            ('done', 'Confirmed'),
        ], 'State', select=True, readonly=True),
        'server' : fields.char('Server Name', size=256, readonly=True, help="Hostname or IP of the mail server", states={'draft':[('readonly', False)]}),
        'port' : fields.integer('Port', readonly=True, states={'draft':[('readonly', False)]}),
        'type':fields.selection([
            ('pop', 'POP Server'),
            ('imap', 'IMAP Server'),
            ('local', 'Local Server'),
        ], 'Server Type', select=True, required=True, readonly=False),
        'is_ssl':fields.boolean('SSL/TLS', help="Connections are encrypted with SSL/TLS through a dedicated port (default: IMAPS=993, POP3S=995)"),
        'attach':fields.boolean('Keep Attachments', help="Whether attachments should be downloaded. "
                                                         "If not enabled, incoming emails will be stripped of any attachments before being processed"),
        'original':fields.boolean('Keep Original', help="Whether a full original copy of each email should be kept for reference"
                                                        "and attached to each processed message. This will usually double the size of your message database."),
        'date': fields.datetime('Last Fetch Date', readonly=True),
        'user' : fields.char('Username', size=256, readonly=True, states={'draft':[('readonly', False)]}),
        'password' : fields.char('Password', size=1024, readonly=True, states={'draft':[('readonly', False)]}),
        'action_id':fields.many2one('ir.actions.server', 'Server Action', help="Optional custom server action to trigger for each incoming mail, "
                                                                               "on the record that was created or updated by this mail"),
        'object_id': fields.many2one('ir.model', "Create a New Record", required=True, help="Process each incoming mail as part of a conversation "
                                                                                             "corresponding to this document type. This will create "
                                                                                             "new documents for new conversations, or attach follow-up "
                                                                                             "emails to the existing conversations (documents)."),
        'priority': fields.integer('Server Priority', readonly=True, states={'draft':[('readonly', False)]}, help="Defines the order of processing, "
                                                                                                                  "lower values mean higher priority"),
        'message_ids': fields.one2many('mail.message', 'fetchmail_server_id', 'Messages', readonly=True),
        'configuration' : fields.text('Configuration'),
        'script' : fields.char('Script', readonly=True, size=64),
    }
    _defaults = {
        'state': "draft",
        'type': "pop",
        'active': True,
        'priority': 5,
        'attach': True,
        'script': '/mail/static/scripts/openerp_mailgate.py',
    }


    def onchange_server_type(self, cr, uid, ids, server_type=False, ssl=False, object_id=False):
        port = 0
        values = {}
        if server_type == 'pop':
            port = ssl and 995 or 110
        elif server_type == 'imap':
            port = ssl and 993 or 143
        else:
            values['server'] = ''
        values['port'] = port

        conf = {
            'dbname' : cr.dbname,
            'uid' : uid,
            'model' : 'MODELNAME',
        }
        if object_id:
            m = self.pool.get('ir.model')
            r = m.read(cr,uid,[object_id],['model'])
            conf['model']=r[0]['model']
        values['configuration'] = """Use the below script with the following command line options with your Mail Transport Agent (MTA)

openerp_mailgate.py -u %(uid)d -p PASSWORD -o %(model)s -d %(dbname)s --host=HOSTNAME --port=PORT 
""" % conf

        return {'value':values}

    def set_draft(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids , {'state':'draft'})
        return True

    def connect(self, cr, uid, server_id, context=None):
        if isinstance(server_id, (list,tuple)):
            server_id = server_id[0]
        server = self.browse(cr, uid, server_id, context)
        if server.type == 'imap':
            if server.is_ssl:
                connection = IMAP4_SSL(server.server, int(server.port))
            else:
                connection = IMAP4(server.server, int(server.port))
            connection.login(server.user, server.password)
        elif server.type == 'pop':
            if server.is_ssl:
                connection = POP3_SSL(server.server, int(server.port))
            else:
                connection = POP3(server.server, int(server.port))
            #TODO: use this to remove only unread messages
            #connection.user("recent:"+server.user)
            connection.user(server.user)
            connection.pass_(server.password)
        return connection

    def button_confirm_login(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        for server in self.browse(cr, uid, ids, context=context):
            try:
                connection = server.connect()
                server.write({'state':'done'})
            except Exception, e:
                logger.exception("Failed to connect to %s server %s", server.type, server.name)
                raise osv.except_osv(_("Connection test failed!"), _("Here is what we got instead:\n %s") % tools.ustr(e))
            finally:
                try:
                    if connection:
                        if server.type == 'imap':
                            connection.close()
                        elif server.type == 'pop':
                            connection.quit()
                except Exception:
                    # ignored, just a consequence of the previous exception
                    pass
        return True

    def _fetch_mails(self, cr, uid, ids=False, context=None):
        if not ids:
            ids = self.search(cr, uid, [('state','=','done')])
        return self.fetch_mail(cr, uid, ids, context=context)

    def fetch_mail(self, cr, uid, ids, context=None):
        """WARNING: meant for cron usage only - will commit() after each email!"""
        if context is None:
            context = {}
        mail_thread = self.pool.get('mail.thread')
        action_pool = self.pool.get('ir.actions.server')
        for server in self.browse(cr, uid, ids, context=context):
            logger.info('start checking for new emails on %s server %s', server.type, server.name)
            context.update({'fetchmail_server_id': server.id, 'server_type': server.type})
            count = 0
            if server.type == 'imap':
                try:
                    imap_server = server.connect()
                    imap_server.select()
                    result, data = imap_server.search(None, '(UNSEEN)')
                    for num in data[0].split():
                        result, data = imap_server.fetch(num, '(RFC822)')
                        res_id = mail_thread.message_process(cr, uid, server.object_id.model, data[0][1],
                                                             save_original=server.original,
                                                             strip_attachments=(not server.attach),
                                                             context=context)
                        if res_id and server.action_id:
                            action_pool.run(cr, uid, [server.action_id.id], {'active_id': res_id, 'active_ids': [res_id], 'active_model': server.object_id.model})
                            imap_server.store(num, '+FLAGS', '\\Seen')
                            cr.commit()
                        count += 1
                    logger.info("fetched/processed %s email(s) on %s server %s", count, server.type, server.name)
                except Exception, e:
                    logger.exception("Failed to fetch mail from %s server %s", server.type, server.name)
                finally:
                    if imap_server:
                        imap_server.close()
                        imap_server.logout()
            elif server.type == 'pop':
                try:
                    pop_server = server.connect()
                    (numMsgs, totalSize) = pop_server.stat()
                    pop_server.list()
                    for num in range(1, numMsgs + 1):
                        (header, msges, octets) = pop_server.retr(num)
                        msg = '\n'.join(msges)
                        res_id = mail_thread.message_process(cr, uid, server.object_id.model,
                                                             msg,
                                                             save_original=server.original,
                                                             strip_attachments=(not server.attach),
                                                             context=context)
                        if res_id and server.action_id:
                            action_pool.run(cr, uid, [server.action_id.id], {'active_id': res_id, 'active_ids': [res_id], 'active_model': server.object_id.model})
                        pop_server.dele(num)
                        cr.commit()
                    logger.info("fetched/processed %s email(s) on %s server %s", numMsgs, server.type, server.name)
                except Exception, e:
                    logger.exception("Failed to fetch mail from %s server %s", server.type, server.name)
                finally:
                    if pop_server:
                        pop_server.quit()
            server.write({'date': time.strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)})
        return True

class mail_message(osv.osv):
    _inherit = "mail.message"
    _columns = {
        'fetchmail_server_id': fields.many2one('fetchmail.server', "Inbound Mail Server",
                                               readonly=True,
                                               select=True,
                                               oldname='server_id'),
    }

    def create(self, cr, uid, values, context=None):
        if context is None:
            context={}
        fetchmail_server_id = context.get('fetchmail_server_id')
        if fetchmail_server_id:
            values['fetchmail_server_id'] = fetchmail_server_id
        res = super(mail_message,self).create(cr, uid, values, context=context)
        return res

    def write(self, cr, uid, ids, values, context=None):
        if context is None:
            context={}
        fetchmail_server_id = context.get('fetchmail_server_id')
        if fetchmail_server_id:
            values['fetchmail_server_id'] = server_id
        res = super(mail_message,self).write(cr, uid, ids, values, context=context)
        return res


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
