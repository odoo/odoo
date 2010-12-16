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
from osv import fields,osv
import tools
import re
import time

class base_synchro_server(osv.osv):
    '''Class to store the information regarding server'''
    _name = "base.synchro.server"
    _description = "Synchronized server"
    _columns = {
        'name': fields.char('Server name', size=64,required=True),
        'server_url': fields.char('Server URL', size=64,required=True),
        'server_port': fields.integer('Server Port', size=64,required=True),
        'server_db': fields.char('Server Database', size=64,required=True),
        'login': fields.char('User Name',size=50,required=True),
        'password': fields.char('Password',size=64,invisible=True,required=True),
        'obj_ids' : fields.one2many('base.synchro.obj','server_id','Models',ondelete='cascade')
    }
    _defaults = {
        'server_port': lambda *args: 8069
    }
base_synchro_server()

class base_synchro_obj(osv.osv):
    '''Class to store the operations done by wizard'''
    _name = "base.synchro.obj"
    _description = "Register Class"
    _columns = {
        'name':fields.char('Name', size=64, select=1, required=1),
        'domain':fields.char('Domain', size=64, select=1, required=1),
        'server_id':fields.many2one('base.synchro.server','Server', ondelete='cascade', select=1, required=1),
        'model_id': fields.many2one('ir.model', 'Object to synchronize',required=True),
        'action':fields.selection([('d','Download'),('u','Upload'),('b','Both')],'Synchronisation direction', required=True),
        'sequence': fields.integer('Sequence'),
        'active': fields.boolean('Active'),
        'synchronize_date':fields.datetime('Latest Synchronization', readonly=True),
        'line_id':fields.one2many('base.synchro.obj.line','obj_id','Ids Affected',ondelete='cascade'),
        'avoid_ids':fields.one2many('base.synchro.obj.avoid','obj_id','Fields Not Sync.'),
    }
    _defaults = {
        'active': lambda *args: True,
        'action': lambda *args: 'd',
        'domain': lambda *args: '[]'
    }
    _order = 'sequence'
    #
    # Return a list of changes: [ (date, id) ]
    #

    def get_ids(self, cr, uid, object, dt, domain=[], context=None):
        return self._get_ids(cr, uid, object, dt, domain, context=context)

    def _get_ids(self, cr, uid, object, dt, domain=[], context=None):
        result = []
        if dt:
            domain2 = domain+[('write_date','>=',dt)]
            domain3 = domain+[('create_date','>=',dt)]
        else:
            domain2 = domain3 = domain
        ids = self.pool.get(object).search(cr, uid, domain2, context=context)
        ids += self.pool.get(object).search(cr, uid, domain3, context=context)
        for r in self.pool.get(object).perm_read(cr, uid, ids, context, details=False):
            result.append( (r['write_date'] or r['create_date'], r['id'], context.get('action', 'd')))
        return result
base_synchro_obj()

class base_synchro_obj_avoid(osv.osv):
    _name = "base.synchro.obj.avoid"
    _description = "Fields to not synchronize"
    _columns = {
        'name':fields.char('Field Name', size=64, select=1, required=1),
        'obj_id':fields.many2one('base.synchro.obj', 'Object', required=1,ondelete='cascade'),
    }
base_synchro_obj_avoid()


class base_synchro_obj_line(osv.osv):
    '''Class to store the operations done by wizard'''
    _name = "base.synchro.obj.line"
    _description = "Synchronized instances"
    _columns = {
        'name': fields.datetime('Date', required=True),
        'obj_id': fields.many2one('base.synchro.obj', 'Object', ondelete='cascade', select=True),
        'local_id': fields.integer('Local Id',readonly=True),
        'remote_id':fields.integer('Remote Id',readonly=True),
    }
    _defaults = {
        'name': lambda *args: time.strftime('%Y-%m-%d %H:%M:%S')
    }
base_synchro_obj_line()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
