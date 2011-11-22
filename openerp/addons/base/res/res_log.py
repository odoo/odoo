# -*- coding: utf-8 -*-
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

from osv import fields, osv

class res_log(osv.osv):
    _name = 'res.log'
    _columns = {
        'name': fields.char('Message', size=250, help='The logging message.', required=True, select=1),
        'user_id': fields.many2one('res.users','User'),
        'res_model': fields.char('Object', size=128, select=1),
        'context': fields.char('Context', size=250),
        'res_id': fields.integer('Object ID'),
        'secondary': fields.boolean('Secondary Log', help='Do not display this log if it belongs to the same object the user is working on'),
        'create_date': fields.datetime('Creation Date', readonly=True, select=1),
        'read': fields.boolean('Read', help="If this log item has been read, get() should not send it to the client"),
    }
    _defaults = {
        'user_id': lambda self,cr,uid,ctx: uid,
        'context': "{}",
        'read': False,
    }
    _order='create_date desc'

    _index_name = 'res_log_uid_read'
    def _auto_init(self, cr, context=None):
        super(res_log, self)._auto_init(cr, context)
        cr.execute('SELECT 1 FROM pg_indexes WHERE indexname=%s',
                   (self._index_name,))
        if not cr.fetchone():
            cr.execute('CREATE INDEX %s ON res_log (user_id, read)' %
                       self._index_name)

    def create(self, cr, uid, vals, context=None):
        create_context = context and dict(context) or {}
        if 'res_log_read' in create_context:
            vals['read'] = create_context.pop('res_log_read')
        if create_context and not vals.get('context'):
            vals['context'] = create_context
        return super(res_log, self).create(cr, uid, vals, context=context)

    # TODO: do not return secondary log if same object than in the model (but unlink it)
    def get(self, cr, uid, context=None):
        unread_log_ids = self.search(cr, uid,
            [('user_id','=',uid), ('read', '=', False)], context=context)
        res = self.read(cr, uid, unread_log_ids,
            ['name','res_model','res_id','context'],
            context=context)
        res.reverse()
        result = []
        res_dict = {}
        for r in res:
            t = (r['res_model'], r['res_id'])
            if t not in res_dict:
                res_dict[t] = True
                result.insert(0,r)
        self.write(cr, uid, unread_log_ids, {'read': True}, context=context)
        return result

res_log()
