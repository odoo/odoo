## -*- coding: utf-8 -*-
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
import osv
from datetime import date
import time
import pooler
import xmlrpclib
import re
import tools
import threading
from osv import osv, fields

class RPCProxyOne(object):
    def __init__(self, server, ressource):
        self.server = server
        local_url = 'http://%s:%d/xmlrpc/common'%(server.server_url,server.server_port)
        rpc = xmlrpclib.ServerProxy(local_url)
        self.uid = rpc.login(server.server_db, server.login, server.password)
        local_url = 'http://%s:%d/xmlrpc/object'%(server.server_url,server.server_port)
        self.rpc = xmlrpclib.ServerProxy(local_url)
        self.ressource = ressource
    def __getattr__(self, name):
        return lambda cr, uid, *args, **kwargs: self.rpc.execute(self.server.server_db, self.uid, self.server.password, self.ressource, name, *args)

class RPCProxy(object):
    def __init__(self, server):
        self.server = server
    def get(self, ressource):
        return RPCProxyOne(self.server, ressource)

class base_synchro(osv.osv_memory):
    """Base Synchronization """
    _name = 'base.synchro'

    _columns = {
    'server_url': fields.many2one('base.synchro.server', "Server URL", required=True),
    'user_id': fields.many2one('res.users', "Send Result To",),
    }

    _defaults = {
        'user_id': lambda self,cr,uid,context: uid,
        }

    start_date = time.strftime('%Y-%m-%d, %Hh %Mm %Ss')
    report = []
    report_total = 0
    report_create = 0
    report_write = 0

    def synchronize(self, cr, uid, server, object, context=None):
        pool = pooler.get_pool(cr.dbname)
        self.meta = {}
        ids = []
        pool1 = RPCProxy(server)
        pool2 = pool
        #try:
        if object.action in ('d','b'):
            ids = pool1.get('base.synchro.obj').get_ids(cr, uid,
                object.model_id.model,
                object.synchronize_date,
                eval(object.domain),
                {'action':'d'}
            )

        if object.action in ('u','b'):
            ids += pool2.get('base.synchro.obj').get_ids(cr, uid,
                object.model_id.model,
                object.synchronize_date,
                eval(object.domain),
                {'action':'u'}
            )
        ids.sort()
        iii = 0
        for dt, id, action in ids:
            print 'Process', dt, id, action
            iii +=1
            if action=='u':
                pool_src = pool2
                pool_dest = pool1
            else:
                pool_src = pool1
                pool_dest = pool2
            print 'Read', object.model_id.model, id
            fields = False
            if object.model_id.model=='crm.case.history':
                fields = ['email','description','log_id']
            value = pool_src.get(object.model_id.model).read(cr, uid, [id], fields)[0]
            value = self.data_transform(cr, uid, pool_src, pool_dest, object.model_id.model, value, action, context=context)
            id2 = self.get_id(cr, uid, object.id, id, action, context)
            #
            # Transform value
            #
            #tid=pool_dest.get(object.model_id.model).name_search(cr, uid, value['name'],[],'=',)
            if not (iii%50):
                print 'Record', iii
            # Filter fields to not sync
            for field in object.avoid_ids:
                if field.name in value:
                    del value[field.name]

            if id2:
                #try:
                pool_dest.get(object.model_id.model).write(cr, uid, [id2], value)
                #except Exception, e:
                #self.report.append('ERROR: Unable to update record ['+str(id2)+']:'+str(value.get('name', '?')))
                self.report_total+=1
                self.report_write+=1
            else:
                print value
                idnew = pool_dest.get(object.model_id.model).create(cr, uid, value)
                synid = self.pool.get('base.synchro.obj.line').create(cr, uid, {
                    'obj_id': object.id,
                    'local_id': (action=='u') and id or idnew,
                    'remote_id': (action=='d') and id or idnew
                })
                self.report_total+=1
                self.report_create+=1
            self.meta = {}
        return True

    def get_id(self, cr, uid, object_id, id, action, context=None):
        pool = pooler.get_pool(cr.dbname)
        line_pool = pool.get('base.synchro.obj.line')
        field_src = (action=='u') and 'local_id' or 'remote_id'
        field_dest = (action=='d') and 'local_id' or 'remote_id'
        rid = line_pool.search(cr, uid, [('obj_id','=',object_id), (field_src,'=',id)], context=context)
        result = False
        if rid:
            result  = line_pool.read(cr, uid, rid, [field_dest], context=context)[0][field_dest]
        return result

    def relation_transform(self, cr, uid, pool_src, pool_dest, object, id, action, context=None):
        if not id:
            return False
        pool = pooler.get_pool(cr.dbname)
        cr.execute('''select o.id from base_synchro_obj o left join ir_model m on (o.model_id =m.id) where
                m.model=%s and
                o.active''', (object,))
        obj = cr.fetchone()
        result = False
        if obj:
            #
            # If the object is synchronised and found, set it
            #
            result = self.get_id(cr, uid, obj[0], id, action, context)
        else:
            #
            # If not synchronized, try to find it with name_get/name_search
            #
            names = pool_src.get(object).name_get(cr, uid, [id], context)[0][1]
            res = pool_dest.get(object).name_search(cr, uid, names, [], 'like')
            if res:
                result = res[0][0]
            else:
                # LOG this in the report, better message.
                print self.report.append('WARNING: Record "%s" on relation %s not found, set to null.' % (names,object))
        return result

    #
    # IN: object and ID
    # OUT: ID of the remote object computed:
    #        If object is synchronised, read the sync database
    #        Otherwise, use the name_search method
    #

    def data_transform(self, cr, uid, pool_src, pool_dest, object, data, action='u', context=None):
        self.meta.setdefault(pool_src, {})
        if not object in self.meta[pool_src]:
            self.meta[pool_src][object] = pool_src.get(object).fields_get(cr, uid, context)
        fields = self.meta[pool_src][object]

        for f in fields:
            if f not in data:
                continue
            ftype = fields[f]['type']

            if ftype in ('function', 'one2many', 'one2one'):
                del data[f]
            elif ftype == 'many2one':
                if data[f]:
                    df = self.relation_transform(cr, uid, pool_src, pool_dest, fields[f]['relation'], data[f][0], action, context=context)
                    data[f] = df
                    if not data[f]:
                        del data[f]
            elif ftype == 'many2many':
                res = map(lambda x: self.relation_transform(cr, uid, pool_src, pool_dest, fields[f]['relation'], x, action, context), data[f])
                data[f] = [(6, 0, res)]
        del data['id']
        return data

    #
    # Find all objects that are created or modified after the synchronize_date
    # Synchronize these obejcts
    #


    def upload_download(self, cr, uid, ids, context=None):
        start_date = time.strftime('%Y-%m-%d, %Hh %Mm %Ss')
        syn_obj = self.browse(cr, uid, ids, context=context)[0]
        pool = pooler.get_pool(cr.dbname)
        server = pool.get('base.synchro.server').browse(cr, uid, syn_obj.server_url.id, context=context)
        for object in server.obj_ids:
            dt = time.strftime('%Y-%m-%d %H:%M:%S')
            self.synchronize(cr, uid, server, object, context=context)
            if object.action=='b':
                time.sleep(1)
                dt = time.strftime('%Y-%m-%d %H:%M:%S')
            self.pool.get('base.synchro.obj').write(cr, uid, [object.id], {'synchronize_date': dt})
        end_date = time.strftime('%Y-%m-%d, %Hh %Mm %Ss')
        if syn_obj.user_id:
            request = pooler.get_pool(cr.dbname).get('res.request')
            if not self.report:
                self.report.append('No exception.')
            summary = '''Here is the synchronization report:

Synchronization started: %s
Synchronization finnished: %s

Synchronized records: %d
Records updated: %d
Records created: %d

Exceptions:
            '''% (start_date,end_date,self.report_total, self.report_write,self.report_create)
            summary += '\n'.join(self.report)
            request.create(cr, uid, {
                'name' : "Synchronization report",
                'act_from' : uid,
                'act_to' : syn_obj.user_id.id,
                'body': summary,
            })
            return True

    def upload_download_multi_thread(self, cr, uid, data, context=None):
        threaded_synchronization = threading.Thread(target=self.upload_download, args=(cr, uid, data, context))
        threaded_synchronization.run()
        data_obj = self.pool.get('ir.model.data')
        id2 = data_obj._get_id(cr, uid, 'base_synchro', 'view_base_synchro_finish')
        if id2:
            id2 = data_obj.browse(cr, uid, id2, context=context).res_id
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'base.synchro',
            'views': [(id2, 'form')],
            'view_id': False,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }
base_synchro()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
