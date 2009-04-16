# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
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

from xml.dom import minidom
from osv import fields,osv
import netsvc
import pooler
import string

installed = False

def fnct_call(fnct):
    def execute(*args, **argv):
        if len(args) >= 6 and isinstance(args[5], dict):
            _old_args = args[5].copy()
        else:
            _old_args = None
        res = fnct(*args, **argv)
        pool = pooler.get_pool(args[0])
        mod = pool.get('ir.module.record')
        if mod and mod.recording:
            if args[4] not in ('default_get','read','fields_view_get','fields_get','search','search_count','name_search','name_get','get','request_get', 'get_sc'):
                if _old_args is not None:
                    args[5].update(_old_args)
                if args[5]:
                    mod.recording_data.append(('query', args, argv,res))
        return res
    return execute

def fnct_call_workflow(fnct):
    def exec_workflow(*args, **argv):
        res = fnct(*args, **argv)
        pool = pooler.get_pool(args[0])
        mod = pool.get('ir.module.record')
        if mod and mod.recording:
            mod.recording_data.append(('workflow', args, argv))
        return res
    return exec_workflow

class base_module_record(osv.osv):
    _name = "ir.module.record"
    _columns = {

    }
    def __init__(self, pool, cr=None):
        global installed
        if super(base_module_record, self).__init__.func_code.co_argcount ==3:
            super(base_module_record, self).__init__(pool,cr)
        else:
            super(base_module_record, self).__init__(pool)
        self.recording = 0
        self.recording_data = []
        self.depends = {}
        if not installed:
            obj = netsvc.SERVICES['object']
            obj.execute = fnct_call(obj.execute)
            obj.exportMethod(obj.execute)
            obj.exec_workflow = fnct_call_workflow(obj.exec_workflow)
            obj.exportMethod(obj.exec_workflow)
            installed = True

    # To Be Improved
    def _create_id(self, cr, uid, model, data):
        i = 0
        while True:
            try:
                name = filter(lambda x: x in string.letters, (data.get('name','') or '').lower())
            except:
                name=''
            val = model.replace('.','_')+'_'+name+ str(i)
            i+=1
            if val not in self.ids.values():
                break
        return val

    def _get_id(self, cr, uid, model, id):
        if type(id)==type(()):
            id=id[0]
        if (model,id) in self.ids:
            return self.ids[(model,id)], False
        dt = self.pool.get('ir.model.data')
        dtids = dt.search(cr, uid, [('model','=',model), ('res_id','=',id)])
        if not dtids:
            return None, None
        obj = dt.browse(cr, uid, dtids[0])
        self.depends[obj.module] = True
        return obj.module+'.'+obj.name, obj.noupdate

    def _create_record(self, cr, uid, doc, model, data, record_id, noupdate=False):
        record = doc.createElement('record')
        record.setAttribute("id", record_id)
        record.setAttribute("model", model)
        record_list = [record]
        lids  = self.pool.get('ir.model.data').search(cr, uid, [('model','=',model)])
        res = self.pool.get('ir.model.data').read(cr, uid, lids[:1], ['module'])
        if res:
            self.depends[res[0]['module']]=True
        fields = self.pool.get(model).fields_get(cr, uid)
        for key,val in data.items():
            if not (val or (fields[key]['type']=='boolean')):
                continue
            if fields[key]['type'] in ('integer','float'):
                field = doc.createElement('field')
                field.setAttribute("name", key)
                field.setAttribute("eval", val and str(val) or 'False' )
                record.appendChild(field)
            elif fields[key]['type'] in ('boolean',):
                field = doc.createElement('field')
                field.setAttribute("name", key)
                field.setAttribute("eval", val and '1' or '0' )
                record.appendChild(field)
            elif fields[key]['type'] in ('many2one',):
                field = doc.createElement('field')
                field.setAttribute("name", key)
                if type(val) in (type(''),type(u'')):
                    id = val
                else:
                    id,update = self._get_id(cr, uid, fields[key]['relation'], val)
                    noupdate = noupdate or update
                if not id:
                    field.setAttribute("model", fields[key]['relation'])
                    name = self.pool.get(fields[key]['relation']).browse(cr, uid, val).name
                    field.setAttribute("search", "[('name','=','"+name+"')]")
                else:
                    field.setAttribute("ref", id)
                record.appendChild(field)
            elif fields[key]['type'] in ('one2many',):
                for valitem in (val or []):
                    if valitem[0] in (0,1):
                        if key in self.pool.get(model)._columns:
                            fname = self.pool.get(model)._columns[key]._fields_id
                        else:
                            fname = self.pool.get(model)._inherit_fields[key][2]._fields_id
                        valitem[2][fname] = record_id
                        newid,update = self._get_id(cr, uid, fields[key]['relation'], valitem[1])
                        if not newid:
                            newid = self._create_id(cr, uid, fields[key]['relation'], valitem[2])
#                        if valitem[0]==0:
#                            newid = self._create_id(cr, uid, fields[key]['relation'], valitem[2])
#                        else:
#                            newid,update = self._get_id(cr, uid, fields[key]['relation'], valitem[1])
                        childrecord, update = self._create_record(cr, uid, doc, fields[key]['relation'],valitem[2], newid)
                        noupdate = noupdate or update
                        record_list += childrecord
                        self.ids[(fields[key]['relation'],newid)] = newid
                    else:
                        pass
            elif fields[key]['type'] in ('many2many',):
                res = []
                for valitem in (val or []):
                    if valitem[0]==6:
                        for id2 in valitem[2]:
                            id,update = self._get_id(cr, uid, fields[key]['relation'], id2)
                            self.ids[(fields[key]['relation'],id)] = id
                            noupdate = noupdate or update
                            res.append(id)
                        field = doc.createElement('field')
                        field.setAttribute("name", key)
                        field.setAttribute("eval", "[(6,0,["+','.join(map(lambda x: "ref('%s')" % (x,), res))+'])]')
                        record.appendChild(field)
            else:
                field = doc.createElement('field')
                field.setAttribute("name", key)

                if not isinstance(val, basestring):
                    val = str(val)

                val = val and ('"""%s"""' % val.replace('\\', '\\\\').replace('"', '\"')) or 'False'
                field.setAttribute(u"eval",  val.decode('utf-8'))
                record.appendChild(field)
        return record_list, noupdate

    def get_copy_data(self, cr, uid, model, id, result):
        res = []
        obj=self.pool.get(model)
        data=obj.read(cr, uid,[id])
        if type(data)==type([]):
            del data[0]['id']
            data=data[0]
        else:
            del data['id']

        mod_fields = obj.fields_get(cr, uid)
        for f in filter(lambda a: isinstance(obj._columns[a], fields.function)\
                    and (not obj._columns[a].store),obj._columns):
            del data[f]

        for key,val in data.items():
            if result.has_key(key):
                continue
            if mod_fields[key]['type'] == 'many2one':
                if type(data[key])==type(True) or type(data[key])==type(1):
                    result[key]=data[key]
                else:
                    result[key]=data[key][0]

            elif mod_fields[key]['type'] in ('one2many',):
                rel = mod_fields[key]['relation']
                if len(data[key]):
                    res1=[]
                    for rel_id in data[key]:
                        res=[0,0]
                        res.append(self.get_copy_data(cr, uid,rel,rel_id,{}))
                        res1.append(res)
                    result[key]=res1
                else:
                    result[key]=data[key]

            elif mod_fields[key]['type'] == 'many2many':
                result[key]=[(6,0,data[key])]

            else:
                result[key]=data[key]
        for k,v in obj._inherits.items():
            del result[v]
        return result

    def _create_function(self, cr, uid, doc, model, name, record_id):
        record = doc.createElement('function')
        record.setAttribute("name", name)
        record.setAttribute("model", model)
        record_list = [record]

        value = doc.createElement('value')
        value.setAttribute('eval', '[ref(\'%s\')]' % (record_id, ))
        value.setAttribute('model', model)

        record.appendChild(value)
        return record_list, False

    def _generate_object_xml(self, cr, uid, rec, recv, doc, result=None):
        record_list = []
        noupdate = False
        if rec[4]=='write':
            for id in rec[5]:
                id,update = self._get_id(cr, uid, rec[3], id)
                noupdate = noupdate or update
                if not id:
                    continue
                record,update = self._create_record(cr, uid, doc, rec[3], rec[6], id)
                noupdate = noupdate or update
                record_list += record

        elif rec[4] in ('menu_create',):
            for id in rec[5]:
                id,update = self._get_id(cr, uid, rec[3], id)
                noupdate = noupdate or update
                if not id:
                    continue
                record,update = self._create_function(cr, uid, doc, rec[3], rec[4], id)
                noupdate = noupdate or update
                record_list += record

        elif rec[4]=='create':
            id = self._create_id(cr, uid, rec[3],rec[5])
            record,noupdate = self._create_record(cr, uid, doc, rec[3], rec[5], id)
            self.ids[(rec[3],result)] = id
            record_list += record

        elif rec[4]=='copy':
            data=self.get_copy_data(cr,uid,rec[3],rec[5],rec[6])
            copy_rec=(rec[0],rec[1],rec[2],rec[3],rec[4],rec[5],data,rec[7])
            rec=copy_rec
            rec_data=[(self.recording_data[0][0],rec,self.recording_data[0][2],self.recording_data[0][3])]
            self.recording_data=rec_data
            id = self._create_id(cr, uid, rec[3],rec[6])
            record,noupdate = self._create_record(cr, uid, doc, rec[3], rec[6], id)
            self.ids[(rec[3],result)] = id
            record_list += record

        return record_list,noupdate

    def _generate_assert_xml(self, rec, doc):
        pass

    def generate_xml(self, cr, uid):
        # Create the minidom document
        if len(self.recording_data):
            self.ids = {}
            doc = minidom.Document()
            terp = doc.createElement("openerp")
            doc.appendChild(terp)
            for rec in self.recording_data:
                if rec[0]=='workflow':
                    rec_id,noupdate = self._get_id(cr, uid, rec[1][3], rec[1][5])
                    if not rec_id:
                        continue
                    data = doc.createElement("data")
                    terp.appendChild(data)
                    wkf = doc.createElement('workflow')
                    data.appendChild(wkf)
                    wkf.setAttribute("model", rec[1][3])
                    wkf.setAttribute("action", rec[1][4])
                    if noupdate:
                        data.setAttribute("noupdate", "1")
                    wkf.setAttribute("ref", rec_id)
                if rec[0]=='query':
                    res_list,noupdate = self._generate_object_xml(cr, uid, rec[1], rec[2], doc, rec[3])
                    data = doc.createElement("data")
                    if noupdate:
                        data.setAttribute("noupdate", "1")
                    if res_list:
                        terp.appendChild(data)
                    for res in res_list:
                        data.appendChild(res)
                elif rec[0]=='assert':
                        pass
            return doc.toprettyxml(indent="\t").encode('utf-8')
base_module_record()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

