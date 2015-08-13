# -*- coding: utf-8 -*-
from openerp.osv import fields, osv

class mail_mail(osv.osv):
    _inherit = "mail.mail"
    _columns = {
        'fetchmail_server_id': fields.many2one('fetchmail.server', "Inbound Mail Server",
                                               readonly=True,
                                               select=True,
                                               oldname='server_id'),
    }

    def create(self, cr, uid, values, context=None):
        if context is None:
            context = {}
        fetchmail_server_id = context.get('fetchmail_server_id')
        if fetchmail_server_id:
            values['fetchmail_server_id'] = fetchmail_server_id
        res = super(mail_mail, self).create(cr, uid, values, context=context)
        return res

    def write(self, cr, uid, ids, values, context=None):
        if context is None:
            context = {}
        fetchmail_server_id = context.get('fetchmail_server_id')
        if fetchmail_server_id:
            values['fetchmail_server_id'] = fetchmail_server_id
        res = super(mail_mail, self).write(cr, uid, ids, values, context=context)
        return res
