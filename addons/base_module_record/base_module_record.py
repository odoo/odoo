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

from xml.dom import minidom
from osv import fields,osv
import pooler
import string
import tools


class xElement(minidom.Element):
    """dom.Element with compact print
    The Element in minidom has a problem: if printed, adds whitespace
    around the text nodes. The standard will not ignore that whitespace.
    This class simply prints the contained nodes in their compact form, w/o
    added spaces.
    """
    def writexml(self, writer, indent="", addindent="", newl=""):
        writer.write(indent)
        minidom.Element.writexml(self, writer, indent='', addindent='', newl='')
        writer.write(newl)

def doc_createXElement(xdoc, tagName):
        e = xElement(tagName)
        e.ownerDocument = xdoc
        return e

import yaml
from tools import yaml_tag # This import is not unused! Do not remove!
# Please do not override yaml_tag here: modify it in server bin/tools/yaml_tag.py

class base_module_record(osv.osv):
    _name = "ir.module.record"
    _columns = {

    }
    def __init__(self, *args, **kwargs):
        self.recording = 0
        self.recording_data = []
        self.depends = {}
        super(base_module_record, self).__init__(*args, **kwargs)

    # To Be Improved
    def _create_id(self, cr, uid, model, data):
        i = 0
        while True:
            try:
                name = filter(lambda x: x in string.letters, (data.get('name','') or '').lower())
            except:
                name=''
#            name=data.get('name','') or ''.lower()
            val = model.replace('.','_')+'_'+ name + str(i)
            i+=1
            if val not in self.ids.values():
                break
        return val

    def _get_id(self, cr, uid, model, id):
        if type(id)==type(()):
            id=id[0]
        if (model,id) in self.ids:
            res_id = self.ids[(model,id)]
            return res_id, False
        dt = self.pool.get('ir.model.data')
        dtids = dt.search(cr, uid, [('model','=',model), ('res_id','=',id)])
        if not dtids:
            return False, None
        obj = dt.browse(cr, uid, dtids[0])
        self.depends[obj.module] = True
        return obj.module+'.'+obj.name, obj.noupdate
    
    def _create_record(self, cr, uid, doc, model, data, record_id, noupdate=False):
        data_pool = self.pool.get('ir.model.data')
        model_pool = self.pool.get(model)
        
        record = doc.createElement('record')
        record.setAttribute("id", record_id)
        record.setAttribute("model", model)
        record_list = [record]
        
        lids  = data_pool.search(cr, uid, [('model','=',model)])
        res = data_pool.read(cr, uid, lids[:1], ['module'])
        if res:
            self.depends[res[0]['module']]=True
        fields = model_pool.fields_get(cr, uid)
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
                    relation_pool = self.pool.get(fields[key]['relation'])
                    
                    field.setAttribute("model", fields[key]['relation'])
                    fld_nm = relation_pool._rec_name
                    name = relation_pool.read(cr, uid, val,[fld_nm])[fld_nm] or False
                    field.setAttribute("search", str([(str(fld_nm) ,'=', name)]))
                else:
                    field.setAttribute("ref", id)
                record.appendChild(field)
            elif fields[key]['type'] in ('one2many',):
                for valitem in (val or []):
                    if valitem[0] in (0,1):
                        if key in model_pool._columns:
                            model_pool._columns[key]._fields_id
                        else:
                            model_pool._inherit_fields[key][2]._fields_id
                        if valitem[0] == 0:
                            newid = self._create_id(cr, uid, fields[key]['relation'], valitem[2])
                            valitem[1]=newid
                        else:
                            newid,update = self._get_id(cr, uid, fields[key]['relation'], valitem[1])
                            if not newid:
                                newid = self._create_id(cr, uid, fields[key]['relation'], valitem[2])
                                valitem[1]=newid
                        self.ids[(fields[key]['relation'], valitem[1])] = newid
                        
                        childrecord, update = self._create_record(cr, uid, doc, fields[key]['relation'],valitem[2], newid)
                        noupdate = noupdate or update
                        record_list += childrecord
                    else:
                        pass
            elif fields[key]['type'] in ('many2many',):
                res = []
                for valitem in (val or []):
                    if valitem[0]==6:
                        for id2 in valitem[2]:
                            id,update = self._get_id(cr, uid, fields[key]['relation'], id2)
                            self.ids[(fields[key]['relation'],id2)] = id
                            noupdate = noupdate or update
                            res.append(id)
                        field = doc.createElement('field')
                        field.setAttribute("name", key)
                        field.setAttribute("eval", "[(6,0,["+','.join(map(lambda x: "ref('%s')" % (x,), res))+'])]')
                        record.appendChild(field)
            else:
                field = doc_createXElement(doc, 'field')
                field.setAttribute("name", key)
                field.appendChild(doc.createTextNode(val))
                record.appendChild(field)

        return record_list, noupdate

    def _create_yaml_record(self, cr, uid, model, data, record_id):
        record={'model': model, 'id': str(record_id)}
        
        model_pool = self.pool.get(model)
        data_pool = self.pool.get('ir.model.data')
        lids  = data_pool.search(cr, uid, [('model','=',model)])
        
        res = data_pool.read(cr, uid, lids[:1], ['module'])
        attrs={}
        if res:
            self.depends[res[0]['module']]=True
        fields = model_pool.fields_get(cr, uid)
        defaults={}
        try:
            defaults[model] = model_pool.default_get(cr, uid, data)
        except:
            defaults[model]={}
        for key,val in data.items():  
            if ((key in defaults[model]) and (val ==  defaults[model][key])) and not(fields[key].get('required',False)):
                continue
            if fields[key]['type'] in ('integer','float'):
                if not val:
                    val=0.0
                attrs[key] = val
            elif not (val or (fields[key]['type']=='function')):
                continue
            elif fields[key]['type'] in ('boolean',):
                if not val:
                    continue
                attrs[key] = val
            elif fields[key]['type'] in ('many2one',):
                if type(val) in (type(''), type(u'')):
                    id = val
                else:
                    id, update = self._get_id(cr, uid, fields[key]['relation'], val)
                attrs[key] = str(id)
            elif fields[key]['type'] in ('one2many',):
                items=[[]]
                for valitem in (val or []):
                    if valitem[0] in (0,1):
                        if key in model_pool._columns:
                            fname = model_pool._columns[key]._fields_id
                        else:
                            fname = model_pool._inherit_fields[key][2]._fields_id
                        del valitem[2][fname] #delete parent_field from child's fields list
                        
                        childrecord = self._create_yaml_record(cr, uid, fields[key]['relation'],valitem[2], None)
                        items[0].append(childrecord['attrs'])
                attrs[key] = items
            elif fields[key]['type'] in ('many2many',):
                if (key in defaults[model]) and (val[0][2] ==  defaults[model][key]):
                    continue
                res = []
                for valitem in (val or []):
                    if valitem[0]==6:
                        for id2 in valitem[2]:
                            id,update = self._get_id(cr, uid, fields[key]['relation'], id2)
                            self.ids[(fields[key]['relation'],id2)] = id
                            res.append(str(id))
                        m2m=[res]
                if m2m[0]:
                    attrs[key] = m2m
            else:
                try:
                    attrs[key]=str(val)
                except:
                    attrs[key]=tools.ustr(val)
                attrs[key]=attrs[key].replace('"','\'')
        record['attrs'] = attrs
        return record

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
                elif not data[key]:
                    result[key] = False
                else:
                    result[key]=data[key][0]

            elif mod_fields[key]['type'] in ('one2many',):
#                continue # due to this start stop recording will not record one2many field
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
        if rec[3]=='write':
            for id in rec[4]:
                id,update = self._get_id(cr, uid, rec[2], id)
                noupdate = noupdate or update
                if not id:
                    continue
                record,update = self._create_record(cr, uid, doc, rec[2], rec[5], id)
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

        elif rec[3]=='create':
            id = self._create_id(cr, uid, rec[2],rec[4])
            record,noupdate = self._create_record(cr, uid, doc, rec[2], rec[4], id)
            self.ids[(rec[2], result)] = id
            record_list += record

        elif rec[3]=='copy':
            data=self.get_copy_data(cr,uid,rec[2],rec[4],rec[5])
            copy_rec=(rec[0],rec[1],rec[2],rec[3],rec[4],data,rec[5])
            rec=copy_rec
            rec_data=[(self.recording_data[0][0],rec,self.recording_data[0][2],self.recording_data[0][3])]
            self.recording_data=rec_data
            id = self._create_id(cr, uid, rec[2],rec[5])
            record,noupdate = self._create_record(cr, uid, doc, rec[2], rec[5], id)
            self.ids[(rec[2], result)] = id
            record_list += record

        return record_list,noupdate

    def _generate_object_yaml(self, cr, uid, rec, result=None):
        if self.mode=="create":
            yml_id = self._create_id(cr, uid, rec[2],rec[4])
            self.ids[(rec[2], result)] = yml_id
            record = self._create_yaml_record(cr, uid, rec[2], rec[4], yml_id)
            return record
        if self.mode=="workflow":
            id,update = self._get_id(cr, uid, rec[2], rec[4])
            data = {}
            data['model'] = rec[2]
            data['action'] = rec[3]
            data['ref'] = id
            return data
        if self.mode=="write":
            id,update = self._get_id(cr, uid, rec[2],rec[4][0])
            record = self._create_yaml_record(cr, uid, rec[2], rec[5], id)
            return record
        data=self.get_copy_data(cr,uid,rec[2],rec[4],rec[5])
        copy_rec=(rec[0],rec[1],rec[2],rec[3],rec[4],data,rec[5])
        rec=copy_rec
        rec_data=[(self.recording_data[0][0],rec,self.recording_data[0][2],self.recording_data[0][3])]
        self.recording_data=rec_data
        id = self._create_id(cr, uid, rec[2],rec[5])
        record = self._create_yaml_record(cr, uid, str(rec[2]), rec[5], id)
        self.ids[(rec[2], result)] = id
        return record

    def _generate_function_yaml(self, cr, uid, args):
        db, uid, model, action, ids, context = args
        temp_context = context.copy()
        active_id = temp_context['active_id']
        active_model = temp_context['active_model']
        active_id, update = self._get_id(cr, uid, active_model, active_id)
        if not active_id:
            active_id = 1
        rec_id, noupdate = self._get_id(cr, uid, model, ids[0])
        temp_context['active_id'] = "ref('%s')"%unicode(active_id)
        temp_context['active_ids'][0] = "ref('%s')"%str(active_id)
        function={}
        function['model'] = model
        function['action'] = action
        attrs = "self.%s(cr, uid, [ref('%s')], {" %(action, rec_id, )
        for k, v in temp_context.iteritems():
            if isinstance(v, str):
                f= "'"+k+"': "+"'%s'"%v + ", "
            else:
                v=str(v).replace('"', '')
                f= "'"+k+"': "+"%s"%v + ", "
            attrs = attrs + f
        attrs=str(attrs)+'})'
        function['attrs'] = attrs
        return function
            
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
                    rec_id,noupdate = self._get_id(cr, uid, rec[1][2], rec[1][4])
                    if not rec_id:
                        continue
                    data = doc.createElement("data")
                    terp.appendChild(data)
                    wkf = doc.createElement('workflow')
                    data.appendChild(wkf)
                    wkf.setAttribute("model", rec[1][2])
                    wkf.setAttribute("action", rec[1][3])
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

    def generate_yaml(self, cr, uid):
        self.ids = {}
        if len(self.recording_data):
            yaml_file='''\n'''
    
            for rec in self.recording_data:
                if rec[1][3] == 'create':
                    self.mode="create"
                elif rec[1][3] == 'write':
                    self.mode="write"
                elif rec[1][3] == 'copy':
                    self.mode="copy"
                elif rec[0] == 'workflow':
                    self.mode="workflow"
                elif rec[0] == 'osv_memory_action':
                    self.mode='osv_memory_action'
                else:
                    continue
                if self.mode == "workflow":
                    record = self._generate_object_yaml(cr, uid, rec[1],rec[0])
                    yaml_file += "!comment Performing a workflow action %s on module %s"%(record['action'], record['model']) + '''\n'''
                    object = yaml.load(unicode('''\n !workflow %s \n'''%record,'iso-8859-1'))
                    yaml_file += str(object) + '''\n\n'''
                elif self.mode == 'osv_memory_action':
                    osv_action = self._generate_function_yaml(cr, uid, rec[1])
                    yaml_file += "!comment Performing an osv_memory action %s on module %s"%(osv_action['action'], osv_action['model']) + '''\n'''
                    osv_action = yaml.load(unicode('''\n !python %s \n'''%osv_action,'iso-8859-1'))
                    yaml_file += str(osv_action) + '''\n'''
                    attrs = yaml.dump(osv_action.attrs, default_flow_style=False)
                    attrs = attrs.replace("''", '"')
                    attrs = attrs.replace("'", '')
                    yaml_file += attrs + '''\n\n'''
                else:
                    record = self._generate_object_yaml(cr, uid, rec[1], rec[3])
                    if self.mode == "create" or self.mode == "copy":
                        yaml_file += "!comment Creating a %s record"%(record['model']) + '''\n'''
                    else:
                        yaml_file += "!comment Modifying a %s record"%(record['model']) + '''\n'''
                    object = yaml.load(unicode('''\n !record %s \n'''%record,'iso-8859-1'))
                    yaml_file += str(object) + '''\n'''
                    attrs = yaml.dump(object.attrs, default_flow_style=False)
                    yaml_file += attrs + '''\n\n'''
                    
        yaml_result=''''''
        for line in yaml_file.split('\n'):
            line=line.replace("''","'")
            if (line.find('!record') == 0) or (line.find('!workflow') == 0) or (line.find('!python') == 0):
                line = "- \n" + "  " + line
            elif line.find('!comment') == 0:
                line=line.replace('!comment','- \n ')   
            elif line.find('- -') != -1:
                line=line.replace('- -','  -')
                line = "    " + line
            else:
                line = "    " + line
            yaml_result += line + '''\n'''
            
        return yaml_result

base_module_record()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

