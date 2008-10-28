# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
#                    Fabien Pinckaers <fp@tiny.Be>
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

from xml.dom import minidom
from osv import fields,osv
import netsvc
import pooler
import string

class base_module_record(osv.osv):
    _name = "ir.module.record"
    _columns = {

    }
    def __init__(self, pool, cr=None):
        if super(base_module_record, self).__init__.func_code.co_argcount ==3:
            super(base_module_record, self).__init__(pool,cr)
        else:
            super(base_module_record, self).__init__(pool)
        self.recording = 0
        self.recording_data = []
        self.depends = {}

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
        lids  = self.pool.get('ir.model.data').search(cr, uid, [('model','=',model)])
        res = self.pool.get('ir.model.data').read(cr, uid, lids[:1], ['module'])
        if res:
            self.depends[res[0]['module']]=True
        record_list = [record]
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
                    if isinstance(name, basestring):
                        name = name.decode('utf8')
                    field.setAttribute("search", "[('name','=','"+name+"')]")
                else:
                    field.setAttribute("ref", id)
                record.appendChild(field)
            elif fields[key]['type'] in ('one2many',):
                for valitem in (val or []):
                    if valitem[0]==0:
                        if key in self.pool.get(model)._columns:
                            fname = self.pool.get(model)._columns[key]._fields_id
                        else:
                            fname = self.pool.get(model)._inherit_fields[key][2]._fields_id
                        valitem[2][fname] = record_id
                        newid = self._create_id(cr, uid, fields[key]['relation'], valitem[2])
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
                if isinstance(val, basestring):
                    val = val.decode('utf8')

                field.setAttribute(u"eval",  val)
                record.appendChild(field)
        return record_list, noupdate

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
        elif rec[4]=='create':
            id = self._create_id(cr, uid, rec[3],rec[5])
            record,noupdate = self._create_record(cr, uid, doc, rec[3], rec[5], id)
            self.ids[(rec[3],result)] = id
            record_list += record
        return record_list,noupdate
    def _generate_assert_xml(self, rec, doc):
        pass
    def generate_xml(self, cr, uid):
        # Create the minidom document
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
        res = doc.toprettyxml(indent="\t")
        return  doc.toprettyxml(indent="\t").encode('utf8')
base_module_record()

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

obj  = netsvc._service['object']
obj.execute = fnct_call(obj.execute)
obj.exportMethod(obj.execute)
obj.exec_workflow = fnct_call_workflow(obj.exec_workflow)
obj.exportMethod(obj.exec_workflow)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

