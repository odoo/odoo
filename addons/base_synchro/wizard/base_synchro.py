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
import wizard
import osv
from datetime import date
import time
import pooler
import xmlrpclib
import re
import tools
import threading

acc_synchro_form = '''<?xml version="1.0"?>
<form string="Transfer Data To Server">
    <field name="server_url" colspan="4"/>
    <newline/>
    <separator string="Control" colspan="4"/>
    <field name="user_id"/>
    <newline/>
</form>'''

acc_synchro_fields = {
    'server_url': {'string':'Server URL', 'type':'many2one', 'relation':'base.synchro.server','required':True},
    'user_id': {'string':'Send Result To', 'type':'many2one', 'relation':'res.users', 'default': lambda uid,data,state: uid},
}

finish_form ='''<?xml version="1.0"?>
<form string="Synchronization Complited!">
    <label string="The synchronisation has been started.\nYou will receive a request when it's done." colspan="4"/>
</form>
'''

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
        return lambda cr, uid, *args, **kwargs: self.rpc.execute(self.server.server_db, self.uid, self.server.password, self.ressource, name, *args, **kwargs)

class RPCProxy(object):
    def __init__(self, server):
        self.server = server
    def get(self, ressource):
        return RPCProxyOne(self.server, ressource)

class wizard_cost_account_synchro(wizard.interface):
    start_date = time.strftime('%Y-%m-%d, %Hh %Mm %Ss')
    report = []
    report_total = 0
    report_create = 0
    report_write = 0
    def _synchronize(self, cr, uid, server, object, context):
        pool = pooler.get_pool(cr.dbname)
        self.meta = {}
        ids = []
        pool1 = RPCProxy(server)
        pool2 = pool
        #try:
        if object.action in ('d','b'):
            ids = pool1.get('base.synchro.obj')._get_ids(cr, uid,
                object.model_id.model,
                object.synchronize_date,
                eval(object.domain),
                {'action':'d'}
            )
        if object.action in ('u','b'):
            ids += pool2.get('base.synchro.obj')._get_ids(cr, uid,
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
            value = self._data_transform(cr, uid, pool_src, pool_dest, object.model_id.model, value, action)
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
                synid = pool.get('base.synchro.obj.line').create(cr, uid, {
                    'obj_id': object.id,
                    'local_id': (action=='u') and id or idnew,
                    'remote_id': (action=='d') and id or idnew
                })
                self.report_total+=1
                self.report_create+=1
        self.meta = {}
        return 'finish'

    #
    # IN: object and ID
    # OUT: ID of the remote object computed:
    #        If object is synchronised, read the sync database
    #        Otherwise, use the name_search method
    #
    def get_id(self, cr, uid, object_id, id, action, context={}):
        pool = pooler.get_pool(cr.dbname)
        field_src = (action=='u') and 'local_id' or 'remote_id'
        field_dest = (action=='d') and 'local_id' or 'remote_id'
        rid = pool.get('base.synchro.obj.line').search(cr, uid, [('obj_id','=',object_id), (field_src,'=',id)], context=context)
        result = False
        if rid:
            result  = pool.get('base.synchro.obj.line').read(cr, uid, rid, [field_dest], context=context)[0][field_dest]
        return result

    def _relation_transform(self, cr, uid, pool_src, pool_dest, object, id, action, context={}):
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

    def _data_transform(self, cr, uid, pool_src, pool_dest, object, data, action='u', context={}):
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
                    df = self._relation_transform(cr, uid, pool_src, pool_dest, fields[f]['relation'], data[f][0], action, context)
                    data[f] = df
                    if not data[f]:
                        del data[f]
            elif ftype == 'many2many':
                res = map(lambda x: self._relation_transform(cr, uid, pool_src, pool_dest, fields[f]['relation'], x, action, context), data[f])
                data[f] = [(6, 0, res)]
        del data['id']
        return data

    #
    # Find all objects that are created or modified after the synchronize_date
    # Synchronize these obejcts
    #
    def _upload_download(self, db_name, uid, data, context):
        cr = pooler.get_db(db_name).cursor()
        start_date = time.strftime('%Y-%m-%d, %Hh %Mm %Ss')
        pool = pooler.get_pool(cr.dbname)
        server = pool.get('base.synchro.server').browse(cr, uid, data['form']['server_url'], context)
        for object in server.obj_ids:
            dt = time.strftime('%Y-%m-%d %H:%M:%S')
            self._synchronize(cr, uid, server, object, context)
            if object.action=='b':
                time.sleep(1)
                dt = time.strftime('%Y-%m-%d %H:%M:%S')
            pool.get('base.synchro.obj').write(cr, uid, [object.id], {'synchronize_date': dt})
            cr.commit()
        end_date = time.strftime('%Y-%m-%d, %Hh %Mm %Ss')
        if 'user_id' in data['form'] and data['form']['user_id']:
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
                'act_to' : data['form']['user_id'],
                'body': summary,
            })
        cr.commit()
        cr.close()
        return 'finish'

    def _upload_download_multi_thread(self, cr, uid, data, context):
        threaded_synchronization = threading.Thread(target=self._upload_download, args=(cr.dbname, uid, data, context))
        threaded_synchronization.start()
        return 'finish'

    states = {
        'init': {
            'actions': [],
            'result': {'type':'form', 'arch':acc_synchro_form, 'fields':acc_synchro_fields, 'state':[('end','Cancel'),('upload_download','Synchronize')]}
        },
        'upload_download': {
            'actions': [],
            'result':{'type':'choice', 'next_state': _upload_download_multi_thread}
        },
        'finish': {
            'actions': [],
            'result':{'type':'form', 'arch':finish_form,'fields':{},'state':[('end','Ok')]}
        },
    }
wizard_cost_account_synchro('account.analytic.account.transfer')
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

