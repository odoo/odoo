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
import tools 

class res_log(osv.osv_memory):
    _name = 'res.log'
    _columns = {
        'name': fields.char('Message', size=128, help='The logging message.', required=True),
        'user_id': fields.many2one('res.users','User', required=True),
        'res_model': fields.char('Object', size=128),
        'res_id': fields.integer('Object ID'),
        'secondary': fields.boolean('Secondary Log', help='Do not display this log if it belongs to the same object the user is working on')
    }
    _defaults = {
        'user_id': lambda self,cr,uid,ctx: uid
    }
    _order='date desc'

    # TODO: do not return secondary log if same object than in the model (but unlink it)
    def get(self, cr, uid, context={}):
        ids = self.search(cr, uid, [('user_id','=',uid)], context=context)
        result = self.read(cr, uid, ids, ['name','res_model','res_id'], context=context)
        self.unlink(cr, uid, ids, context=context)
        return result

    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        res = []
        log_ids = super(res_log, self).search(cr, uid, args, offset, limit, order, context, count)
        logs = {}
        for log in self.browse(cr, uid, log_ids, context=context):
            res_dict = logs.get(log.res_model, {})
            res_dict.update({log.res_id: log.id})
            logs.update({log.res_model: res_dict})
        res = map(lambda x: x.values(), logs.values())
        return tools.flatten(res)

res_log()

