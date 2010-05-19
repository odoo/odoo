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

class res_log(osv.osv_memory):
    _name = 'res.log'
    _columns = {
        'name': fields.char('Message', size=128, help='The logging message.', required=True),
        'user_id': fields.many2one('res.users','User', required=True),
        'res_model': fields.char('Object', size=128),
        'res_id': fields.integer('Object ID')
    }
    _defaults = {
        'user_id': lambda self,cr,uid,ctx: uid
    }
    _order='id desc'
    def get(self, cr, uid, context={}):
        ids = self.search(cr, uid, [('user_id','=',uid)], context=context)
        result = self.read(cr, uid, ids, ['name','res_model','res_id'], context=context)
        self.unlink(cr, uid, ids, context=context)
        return result
res_log()

