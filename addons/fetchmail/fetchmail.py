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

import time

from imaplib import IMAP4
from imaplib import IMAP4_SSL
from poplib import POP3
from poplib import POP3_SSL

import netsvc
from osv import osv, fields
import tools

logger = netsvc.Logger()


class email_server(osv.osv):

    _name = 'email.server'
    _description = "POP/IMAP Server"

    _columns = {
        'name':fields.char('Name', size=256, required=True, readonly=False),
        'active':fields.boolean('Active', required=False),
        'state':fields.selection([
            ('draft', 'Not Confirmed'),
            ('waiting', 'Waiting for Verification'),
            ('done', 'Confirmed'),
        ], 'State', select=True, readonly=True),
        'server' : fields.char('Server', size=256, required=True, readonly=True, states={'draft':[('readonly', False)]}),
        'port' : fields.integer('Port', required=True, readonly=True, states={'draft':[('readonly', False)]}),
        'type':fields.selection([
            ('pop', 'POP Server'),
            ('imap', 'IMAP Server'),
        ], 'Server Type', select=True, readonly=False),
        'is_ssl':fields.boolean('SSL ?', required=False),
        'attach':fields.boolean('Add Attachments ?', required=False, help="Fetches mail with attachments if true."),
        'date': fields.date('Date', readonly=True, states={'draft':[('readonly', False)]}),
        'user' : fields.char('User Name', size=256, required=True, readonly=True, states={'draft':[('readonly', False)]}),
        'password' : fields.char('Password', size=1024, invisible=True, required=True, readonly=True, states={'draft':[('readonly', False)]}),
        'note': fields.text('Description'),
        'action_id':fields.many2one('ir.actions.server', 'Email Server Action', required=False, domain="[('state','=','email')]", help="An Email Server Action. It will be run whenever an e-mail is fetched from server."),
        'object_id': fields.many2one('ir.model', "Model", required=True, help="OpenObject Model. Generates a record of this model.\nSelect Object with message_new attrbutes."),
        'priority': fields.integer('Server Priority', readonly=True, states={'draft':[('readonly', False)]}, help="Priority between 0 to 10, select define the order of Processing"),
        'user_id':fields.many2one('res.users', 'User', required=False),
        'message_ids': fields.one2many('email.message', 'server_id', 'Messages', readonly=True),
    }
    _defaults = {
        'state': lambda *a: "draft",
        'active': lambda *a: True,
        'priority': lambda *a: 5,
        'date': lambda *a: time.strftime('%Y-%m-%d'),
        'user_id': lambda self, cr, uid, ctx: uid,
    }

    def check_duplicate(self, cr, uid, ids, context=None):
        # RFC *-* Why this limitation? why not in SQL constraint?
        vals = self.read(cr, uid, ids, ['user', 'password'], context=context)[0]
        cr.execute("select count(id) from email_server where user=%s and password=%s", (vals['user'], vals['password']))
        res = cr.fetchone()
        if res:
            if res[0] > 1:
                return False
        return True

    def check_model(self, cr, uid, ids, context = None):
        if context is None:
            context = {}
        current_rec = self.read(cr, uid, ids, context)
        if current_rec:
            current_rec = current_rec[0]
            model_name = self.pool.get('ir.model').browse(cr, uid, current_rec.get('object_id')[0]).model
            model = self.pool.get(model_name)
            if hasattr(model, 'message_new'):
                return True
        return False

    _constraints = [
        (check_duplicate, 'Warning! Can\'t have duplicate server configuration!', ['user', 'password']),
        (check_model, 'Warning! Record for selected Model can not be created\nPlease choose valid Model', ['object_id'])
    ]

    def onchange_server_type(self, cr, uid, ids, server_type=False, ssl=False):
        port = 0
        if server_type == 'pop':
            port = ssl and 995 or 110
        elif server_type == 'imap':
            port = ssl and 993 or 143

        return {'value':{'port':port}}

    def set_draft(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids , {'state':'draft'})
        return True

    def button_confirm_login(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        for server in self.browse(cr, uid, ids, context=context):
            logger.notifyChannel(server.type, netsvc.LOG_INFO, 'fetchmail start checking for new emails on %s' % (server.name))
            context.update({'server_id': server.id})
            try:
                if server.type == 'imap':
                    imap_server = None
                    if server.is_ssl:
                        imap_server = IMAP4_SSL(server.server, int(server.port))
                    else:
                        imap_server = IMAP4(server.server, int(server.port))

                    imap_server.login(server.user, server.password)
                    ret_server = imap_server

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
                    ret_server = pop_server

                self.write(cr, uid, [server.id], {'state':'done'})
                if context.get('get_server',False):
                    return ret_server
            except Exception, e:
                logger.notifyChannel(server.type, netsvc.LOG_WARNING, '%s' % (e))
        return True

    def button_fetch_mail(self, cr, uid, ids, context=None):
        self.fetch_mail(cr, uid, ids, context=context)
        return True

    def _fetch_mails(self, cr, uid, ids=False, context=None):
        if not ids:
            ids = self.search(cr, uid, [])
        return self.fetch_mail(cr, uid, ids, context=context)

    def fetch_mail(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        email_tool = self.pool.get('email.server.tools')
        action_pool = self.pool.get('ir.actions.server')
        context.update({'get_server': True})
        for server in self.browse(cr, uid, ids, context=context):
            count = 0
            user = server.user_id.id or uid
            if server.type == 'imap':
                try:
                    imap_server = self.button_confirm_login(cr, uid, [server.id], context=context)
                    imap_server.select()
                    result, data = imap_server.search(None, '(UNSEEN)')
                    for num in data[0].split():
                        result, data = imap_server.fetch(num, '(RFC822)')
                        res_id = email_tool.process_email(cr, user, server.object_id.model, data[0][1], attach=server.attach, context=context)
                        if res_id and server.action_id:
                            action_pool.run(cr, user, [server.action_id.id], {'active_id': res_id, 'active_ids':[res_id]})

                            imap_server.store(num, '+FLAGS', '\\Seen')
                        count += 1
                    logger.notifyChannel(server.type, netsvc.LOG_INFO, 'fetchmail fetch/process %s email(s) from %s' % (count, server.name))

                except Exception, e:
                    logger.notifyChannel(server.type, netsvc.LOG_WARNING, '%s' % (tools.ustr(e)))
                finally:
                    if imap_server:
                        imap_server.close()
                        imap_server.logout()
            elif server.type == 'pop':
                try:
                    pop_server = self.button_confirm_login(cr, uid, [server.id], context=context)
                    (numMsgs, totalSize) = pop_server.stat()
                    pop_server.list()
                    for num in range(1, numMsgs + 1):
                        (header, msges, octets) = pop_server.retr(num)
                        msg = '\n'.join(msges)
                        res_id = email_tool.process_email(cr, user, server.object_id.model, msg, attach=server.attach, context=context)
                        if res_id and server.action_id:
                            action_pool.run(cr, user, [server.action_id.id], {'active_id': res_id, 'active_ids':[res_id]})

                        pop_server.dele(num)
                    logger.notifyChannel(server.type, netsvc.LOG_INFO, 'fetchmail fetch %s email(s) from %s' % (numMsgs, server.name))
                except Exception, e:
                    logger.notifyChannel(server.type, netsvc.LOG_WARNING, '%s' % (tools.ustr(e)))
                finally:
                    if pop_server:
                        pop_server.quit()
        return True

email_server()

class email_message(osv.osv):

    _inherit = "email.message"

    _columns = {
        'server_id': fields.many2one('email.server', "Mail Server", readonly=True, select=True),
    }

    def create(self, cr, uid, values, context=None):
        if context is None:
            context={}
        server_id = context.get('server_id',False)
        if server_id:
            values['server_id'] = server_id
        res = super(email_message,self).create(cr, uid, values, context=context)
        return res

    def write(self, cr, uid, ids, values, context=None):
        if context is None:
            context={}
        server_id = context.get('server_id',False)
        if server_id:
            values['server_id'] = server_id
        res = super(email_message,self).write(cr, uid, ids, values, context=context)
        return res

email_message()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
