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


import ir
from osv import fields, osv
import netsvc
import pooler
import time
from tools.translate import _


class audittrail_rule(osv.osv):
    _name = 'audittrail.rule'
    _columns = {
        "name": fields.char("Rule Name", size=32, required=True),
        "object_id": fields.many2one('ir.model', 'Object', required=True),
        "user_id": fields.many2many('res.users', 'audittail_rules_users', 'user_id', 'rule_id', 'Users'),
        "log_read": fields.boolean("Log reads"),
        "log_write": fields.boolean("Log writes"),
        "log_unlink": fields.boolean("Log deletes"),
        "log_create": fields.boolean("Log creates"),
        "state": fields.selection((("draft", "Draft"),("subscribed", "Subscribed")), "State", required=True),
        "action_id":fields.many2one('ir.actions.act_window',"Action ID"),
    }

    _defaults = {
        'state': lambda *a: 'draft',
        'log_create': lambda *a: 1,
        'log_unlink': lambda *a: 1,
        'log_write': lambda *a: 1,
    }

    _sql_constraints = [
        ('model_uniq', 'unique (object_id)', """There is a rule defined on this object\n You can not define other on the same!""")
    ]
    __functions = {}

    def subscribe(self, cr, uid, ids, *args):
        for thisrule in self.browse(cr, uid, ids):
            obj = self.pool.get(thisrule.object_id.model)
            if not obj:
                raise osv.except_osv(
                        _('WARNING:audittrail is not part of the pool'),
                        _('Change audittrail depends -- Setting rule as DRAFT'))
                self.write(cr, uid, [thisrule.id], {"state": "draft"})
            val={
                 "name":'View Log',
                 "res_model":'audittrail.log',
                 "src_model":thisrule.object_id.model,
                 "domain":"[('object_id','=',"+str(thisrule.object_id.id)+"),('res_id', '=', active_id)]"

            }
            id=self.pool.get('ir.actions.act_window').create(cr, uid, val)
            self.write(cr, uid, [thisrule.id], {"state": "subscribed","action_id":id})
            keyword = 'client_action_relate'
            value = 'ir.actions.act_window,'+str(id)
            res=self.pool.get('ir.model.data').ir_set(cr, uid, 'action', keyword,'View_log_'+thisrule.object_id.model, [thisrule.object_id.model], value, replace=True, isobject=True, xml_id=False)
        return True

    def unsubscribe(self, cr, uid, ids, *args):
        for thisrule in self.browse(cr, uid, ids):
            if thisrule.id in self.__functions :
                for function in self.__functions[thisrule.id]:
                    setattr(function[0], function[1], function[2])
            w_id=self.pool.get('ir.actions.act_window').search(cr, uid, [('name','=','View Log'),('res_model','=','audittrail.log'),('src_model','=',thisrule.object_id.model)])
            self.pool.get('ir.actions.act_window').unlink(cr, uid,w_id )
            val_obj=self.pool.get('ir.values')
            value="ir.actions.act_window"+','+str(w_id[0])
            val_id=val_obj.search(cr, uid, [('model','=',thisrule.object_id.model),('value','=',value)])
            if val_id:
                res = ir.ir_del(cr, uid, val_id[0])
            self.write(cr, uid, [thisrule.id], {"state": "draft"})
        return True

audittrail_rule()


class audittrail_log(osv.osv):
    _name = 'audittrail.log'
    _columns = {
        "name": fields.char("Name", size=32),
        "object_id": fields.many2one('ir.model', 'Object'),
        "user_id": fields.many2one('res.users', 'User'),
        "method": fields.selection((('read', 'Read'), ('write', 'Write'), ('unlink', 'Delete'), ('create', 'Create')), "Method"),
        "timestamp": fields.datetime("Date"),
        "res_id":fields.integer('Resource Id'),
        "line_ids":fields.one2many('audittrail.log.line','log_id','Log lines')

    }
    _defaults = {
        "timestamp": lambda *a: time.strftime("%Y-%m-%d %H:%M:%S")
    }
    _order = "timestamp desc"

audittrail_log()


class audittrail_log_line(osv.osv):
    _name='audittrail.log.line'
    _columns={
              'field_id': fields.many2one('ir.model.fields','Fields', required=True),
              'log_id':fields.many2one('audittrail.log','Log'),
              'log':fields.integer("Log ID"),
              'old_value':fields.text("Old Value"),
              'new_value':fields.text("New Value"),
              'old_value_text':fields.text('Old value Text' ),
              'new_value_text':fields.text('New value Text' ),
              'field_description':fields.char('Field Description' ,size=64),
              }

audittrail_log_line()


objects_proxy = netsvc.SERVICES['object'].__class__


class audittrail_objects_proxy(objects_proxy):
    def get_value_text(self, cr, uid, field_name, values, object, context=None):
        if context is None:
            context = {}

        pool = pooler.get_pool(cr.dbname)
        obj=pool.get(object.model)
        object_name=obj._name
        obj_ids= pool.get('ir.model').search(cr, uid,[('model','=',object_name)])
        model_object=pool.get('ir.model').browse(cr,uid,obj_ids)[0]
        f_id= pool.get('ir.model.fields').search(cr, uid,[('name','=',field_name),('model_id','=',object.id)])
        if f_id:
            field=pool.get('ir.model.fields').read(cr, uid,f_id)[0]
            model=field['relation']

            if field['ttype']=='many2one':
                if values:
                    if type(values)==tuple:
                        values=values[0]
                    val=pool.get(model).read(cr,uid,[values],[pool.get(model)._rec_name])
                    if len(val):
                        return val[0][pool.get(model)._rec_name]
            elif field['ttype'] == 'many2many':
                value=[]
                if values:
                    for id in values:
                        val=pool.get(model).read(cr,uid,[id],[pool.get(model)._rec_name])
                        if len(val):
                            value.append(val[0][pool.get(model)._rec_name])
                return value

            elif field['ttype'] == 'one2many':

                if values:
                    value=[]
                    for id in values:
                        val=pool.get(model).read(cr,uid,[id],[pool.get(model)._rec_name])

                        if len(val):
                            value.append(val[0][pool.get(model)._rec_name])
                    return value
        return values

    def create_log_line(self, cr, uid, id, object, lines=[]):
        pool = pooler.get_pool(cr.dbname)
        obj=pool.get(object.model)
        object_name=obj._name
        obj_ids= pool.get('ir.model').search(cr, uid,[('model','=',object_name)])
        model_object=pool.get('ir.model').browse(cr,uid,obj_ids)[0]
        for line in lines:
            f_id= pool.get('ir.model.fields').search(cr, uid,[('name','=',line['name']),('model_id','=',object.id)])
            if len(f_id):
                fields=pool.get('ir.model.fields').read(cr, uid,f_id)
                old_value='old_value' in line and  line['old_value'] or ''
                new_value='new_value' in line and  line['new_value'] or ''
                old_value_text='old_value_text' in line and  line['old_value_text'] or ''
                new_value_text='new_value_text' in line and  line['new_value_text'] or ''

                if fields[0]['ttype']== 'many2one':
                    if type(old_value)==tuple:
                        old_value=old_value[0]
                    if type(new_value)==tuple:
                        new_value=new_value[0]
                log_line_id = pool.get('audittrail.log.line').create(cr, uid, {"log_id": id, "field_id": f_id[0] ,"old_value":old_value ,"new_value":new_value,"old_value_text":old_value_text ,"new_value_text":new_value_text,"field_description":fields[0]['field_description']})
                cr.commit()
        return True

    def log_fct(self, db, uid, passwd, object, method, fct_src, *args):
        logged_uids = []
        pool = pooler.get_pool(db)
        cr = pooler.get_db(db).cursor()
        obj=pool.get(object)
        object_name=obj._name
        obj_ids= pool.get('ir.model').search(cr, uid,[('model','=',object_name)])
        model_object=pool.get('ir.model').browse(cr,uid,obj_ids)[0]
        if method in ('create'):
            res_id = fct_src( db, uid, passwd, object, method, *args)
            cr.commit()
            new_value=pool.get(model_object.model).read(cr,uid,[res_id],args[0].keys())[0]
            if 'id' in new_value:
                del new_value['id']
            if not len(logged_uids) or uid in logged_uids:
                id=pool.get('audittrail.log').create(cr, uid, {"method": method , "object_id": model_object.id, "user_id": uid, "res_id": res_id,"name": "%s %s %s" % (method , model_object.id, time.strftime("%Y-%m-%d %H:%M:%S"))})
                lines=[]
                for field in new_value:
                    if new_value[field]:
                        line={
                              'name':field,
                              'new_value':new_value[field],
                              'new_value_text': self.get_value_text(cr,uid,field,new_value[field],model_object)
                              }
                        lines.append(line)
                self.create_log_line(cr,uid,id,model_object,lines)
            cr.commit()
            cr.close()
            return res_id

        if method in ('write'):
            res_ids=args[0]
            for res_id in res_ids:
                old_values=pool.get(model_object.model).read(cr,uid,res_id,args[1].keys())
                old_values_text={}
                for field in args[1].keys():
                    old_values_text[field] = self.get_value_text(cr,uid,field,old_values[field],model_object)
                res =fct_src( db, uid, passwd, object, method, *args)
                cr.commit()
                if res:
                    new_values=pool.get(model_object.model).read(cr,uid,res_ids,args[1].keys())[0]
                    if not len(logged_uids) or uid in logged_uids:
                        id=pool.get('audittrail.log').create(cr, uid, {"method": method, "object_id": model_object.id, "user_id": uid, "res_id": res_id,"name": "%s %s %s" % (method , model_object.id, time.strftime("%Y-%m-%d %H:%M:%S"))})
                        lines=[]
                        for field in args[1].keys():
                            if args[1].keys():
                                line={
                                      'name':field,
                                      'new_value':field in new_values and new_values[field] or '',
                                      'old_value':field in old_values and old_values[field] or '',
                                      'new_value_text': self.get_value_text(cr,uid,field,new_values[field],model_object),
                                      'old_value_text':old_values_text[field]
                                      }
                                lines.append(line)
                        cr.commit()
                        self.create_log_line(cr,uid,id,model_object,lines)
                cr.close()
                return res

        if method in ('read'):
            res_ids=args[0]
            old_values={}
            res =fct_src( db, uid, passwd, object, method, *args)
            if type(res)==list:

                for v in res:
                    old_values[v['id']]=v
            else:
                old_values[res['id']]=res
            for res_id in old_values:
                if not len(logged_uids) or uid in logged_uids:
                    id=pool.get('audittrail.log').create(cr, uid, {"method": method , "object_id": model_object.id, "user_id": uid, "res_id": res_id,"name": "%s %s %s" % (method , model_object.id, time.strftime("%Y-%m-%d %H:%M:%S"))})
                    lines=[]
                    for field in old_values[res_id]:
                        if old_values[res_id][field]:
                            line={
                                      'name':field,
                                      'old_value':old_values[res_id][field],
                                      'old_value_text': self.get_value_text(cr,uid,field,old_values[res_id][field],model_object)
                                      }
                            lines.append(line)
                cr.commit()
                self.create_log_line(cr,uid,id,model_object,lines)
            cr.close()
            return res

        if method in ('unlink'):
            res_ids=args[0]
            old_values={}
            for res_id in res_ids:
                old_values[res_id]=pool.get(model_object.model).read(cr,uid,res_id,[])

            for res_id in res_ids:
                if not len(logged_uids) or uid in logged_uids:
                    id=pool.get('audittrail.log').create(cr, uid, {"method": method , "object_id": model_object.id, "user_id": uid, "res_id": res_id,"name": "%s %s %s" % (method, model_object,  time.strftime("%Y-%m-%d %H:%M:%S"))})
                    lines=[]
                    for field in old_values[res_id]:
                        if old_values[res_id][field]:
                            line={
                                  'name':field,
                                  'old_value':old_values[res_id][field],
                                  'old_value_text': self.get_value_text(cr,uid,field,old_values[res_id][field],model_object)
                                  }
                            lines.append(line)
                    cr.commit()
                    self.create_log_line(cr,uid,id,model_object,lines)
            res =fct_src( db, uid, passwd, object, method, *args)
            cr.close()
            return res
        cr.close()

    def execute(self, db, uid, passwd, model, method, *args):
        pool = pooler.get_pool(db)
        cr = pooler.get_db(db).cursor()
        cr.autocommit(True)
        try:
            proxy = pool.get(model)
            if proxy is None:
                raise Exception('Unknown model: %r' % (model,))

            logged_uids = []
            model_name = proxy._name

            fct_src = super(audittrail_objects_proxy, self).execute

            field = method
            rule = False
            obj_ids= pool.get('ir.model').search(cr, uid,[('model','=',model_name)])
            for obj_name in pool.obj_list():
                if obj_name == 'audittrail.rule':
                    rule = True
            if not rule:
                return fct_src(db, uid, passwd, model, method, *args)
            if not len(obj_ids):
                return fct_src(db, uid, passwd, model, method, *args)
            rule_ids = pool.get('audittrail.rule').search(cr, uid, [('object_id','=',obj_ids[0]),('state','=','subscribed')])
            if not len(rule_ids):
                return fct_src(db, uid, passwd, model, method, *args)

            for thisrule in pool.get('audittrail.rule').browse(cr, uid, rule_ids):
                for user in thisrule.user_id:
                    logged_uids.append(user.id)
                if not len(logged_uids) or uid in logged_uids:
                    if field in ('read','write','create','unlink'):
                        if getattr(thisrule, 'log_'+field):
                            return self.log_fct(db, uid, passwd, model, method, fct_src, *args)
                return fct_src(db, uid, passwd, model, method, *args)
        finally:
            cr.close()

audittrail_objects_proxy()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

