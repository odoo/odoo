# -*- encoding: utf-8 -*-

from osv import osv, fields
import time, pooler, copy
import ir
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

    def __init__(self,pool,cr=None):
        for obj_name in pool.obj_list():
            obj=pool.get(obj_name)
            for field in ('read','write','create','unlink'):
                setattr(obj, field, self.logging_fct(getattr(obj,field), obj))
        super(audittrail_rule, self).__init__(pool,cr)

    def subscribe(self, cr, uid, ids, *args):
        for thisrule in self.browse(cr, uid, ids):
            obj = self.pool.get(thisrule.object_id.model)
            if not obj:
                raise osv.except_osv(
                        'WARNING:audittrail is not part of the pool',
                        'Change audittrail depends -- Setting rule as DRAFT')
                self.write(cr, uid, [thisrule.id], {"state": "draft"})
        val={
             "name":'View Log',
             "res_model":'audittrail.log',
             "src_model":thisrule.object_id.model,
             "domain":"[('res_id', '=', active_id)]"

        }
        id=self.pool.get('ir.actions.act_window').create(cr, uid, val)
        self.write(cr, uid, ids, {"state": "subscribed","action_id":id})
        keyword = 'client_action_relate'
        value = 'ir.actions.act_window,'+str(id)
        res=self.pool.get('ir.model.data').ir_set(cr, uid, 'action', keyword,'View_log_'+thisrule.object_id.model, [thisrule.object_id.model], value, replace=True, isobject=True, xml_id=False)
        return True


    def logging_fct(self, fct_src, obj):
        object_name=obj._name
        object=None
        logged_uids = []
        def get_value_text(cr, uid, field_name,values,object, context={}):
            f_id= self.pool.get('ir.model.fields').search(cr, uid,[('name','=',field_name),('model_id','=',object.id)])
            if f_id:
                field=self.pool.get('ir.model.fields').read(cr, uid,f_id)[0]
                model=field['relation']

                if field['ttype']=='many2one':
                    if values:
                        if type(values)==tuple:
                            values=values[0]
                        val=self.pool.get(model).read(cr,uid,[values],['name'])
                        if len(val):
                            return val[0]['name']

                elif field['ttype'] == 'many2many':
                    value=[]
                    if values:
                        for id in values:
                            val=self.pool.get(model).read(cr,uid,[id],['name'])
                            if len(val):
                                value.append(val[0]['name'])
                    return value

                elif field['ttype'] == 'one2many':

                    if values:
                        value=[]
                        for id in values:
                            val=self.pool.get(model).read(cr,uid,[id],['name'])
                            if len(val):
                                value.append(val[0]['name'])
                        return value
            return values

        def create_log_line(cr,uid,id,object,lines=[]):
            for line in lines:
                f_id= self.pool.get('ir.model.fields').search(cr, uid,[('name','=',line['name']),('model_id','=',object.id)])
                if len(f_id):
                    fields=self.pool.get('ir.model.fields').read(cr, uid,f_id)
                    old_value='old_value' in line and  line['old_value'] or ''
                    new_value='new_value' in line and  line['new_value'] or ''
                    old_value_text='old_value_text' in line and  line['old_value_text'] or ''
                    new_value_text='new_value_text' in line and  line['new_value_text'] or ''

                    if fields[0]['ttype']== 'many2one':
                        if type(old_value)==tuple:
                            old_value=old_value[0]
                        if type(new_value)==tuple:
                            new_value=new_value[0]
                    self.pool.get('audittrail.log.line').create(cr, uid, {"log_id": id, "field_id": f_id[0] ,"old_value":old_value ,"new_value":new_value,"old_value_text":old_value_text ,"new_value_text":new_value_text,"field_description":fields[0]['field_description']})
            return True

        def my_fct( cr, uid, *args, **args2):
            obj_ids= self.pool.get('ir.model').search(cr, uid,[('model','=',object_name)])
            if not len(obj_ids):
                return fct_src(cr, uid, *args, **args2)
            object=self.pool.get('ir.model').browse(cr,uid,obj_ids)[0]
            rule_ids=self.search(cr, uid, [('object_id','=',obj_ids[0]),('state','=','subscribed')])
            if not len(rule_ids):
                return fct_src(cr, uid, *args, **args2)

            field=fct_src.__name__
            for thisrule in self.browse(cr, uid, rule_ids):
                if not getattr(thisrule, 'log_'+field):
                    return fct_src(cr, uid, *args, **args2)
                self.__functions.setdefault(thisrule.id, [])
                self.__functions[thisrule.id].append( (obj,field, getattr(obj,field)) )
                for user in thisrule.user_id:
                    logged_uids.append(user.id)

            if fct_src.__name__ in ('create'):
                res_id =fct_src( cr, uid, *args, **args2)
                new_value=self.pool.get(object.model).read(cr,uid,[res_id],args[0].keys())[0]
                if 'id' in new_value:
                    del new_value['id']
                if not len(logged_uids) or uid in logged_uids:
                    id=self.pool.get('audittrail.log').create(cr, uid, {"method": fct_src.__name__, "object_id": object.id, "user_id": uid, "res_id": res_id,"name": "%s %s %s" % (fct_src.__name__, object.id, time.strftime("%Y-%m-%d %H:%M:%S"))})
                    lines=[]
                    for field in new_value:
                        if new_value[field]:
                            line={
                                  'name':field,
                                  'new_value':new_value[field],
                                  'new_value_text':get_value_text(cr,uid,field,new_value[field],object)
                                  }
                            lines.append(line)
                    create_log_line(cr,uid,id,object,lines)
                return res_id

            if fct_src.__name__ in ('write'):
                res_ids=args[0]
                for res_id in res_ids:
                    old_values=self.pool.get(object.model).read(cr,uid,res_id,args[1].keys())
                    old_values_text={}
                    for field in args[1].keys():
                        old_values_text[field]=get_value_text(cr,uid,field,old_values[field],object)
                    res =fct_src( cr, uid, *args, **args2)
                    if res:
                        new_values=self.pool.get(object.model).read(cr,uid,res_ids,args[1].keys())[0]
                        if not len(logged_uids) or uid in logged_uids:
                            id=self.pool.get('audittrail.log').create(cr, uid, {"method": fct_src.__name__, "object_id": object.id, "user_id": uid, "res_id": res_id,"name": "%s %s %s" % (fct_src.__name__, object.id, time.strftime("%Y-%m-%d %H:%M:%S"))})
                            lines=[]
                            for field in args[1].keys():
                                if args[1].keys():
                                    line={
                                          'name':field,
                                          'new_value':field in new_values and new_values[field] or '',
                                          'old_value':field in old_values and old_values[field] or '',
                                          'new_value_text':get_value_text(cr,uid,field,new_values[field],object),
                                          'old_value_text':old_values_text[field]
                                          }
                                    lines.append(line)
                            create_log_line(cr,uid,id,object,lines)
                    return res

            if fct_src.__name__ in ('read'):
                res_ids=args[0]
                old_values={}
                res =fct_src( cr, uid,*args, **args2)
                if type(res)==list:

                    for v in res:
                        old_values[v['id']]=v
                else:

                    old_values[res['id']]=res
                for res_id in old_values:
                    if not len(logged_uids) or uid in logged_uids:
                        id=self.pool.get('audittrail.log').create(cr, uid, {"method": fct_src.__name__, "object_id": object.id, "user_id": uid, "res_id": res_id,"name": "%s %s %s" % (fct_src.__name__, object.id, time.strftime("%Y-%m-%d %H:%M:%S"))})
                        lines=[]
                        for field in old_values[res_id]:
                            if old_values[res_id][field]:
                                line={
                                          'name':field,
                                          'old_value':old_values[res_id][field],
                                          'old_value_text':get_value_text(cr,uid,field,old_values[res_id][field],object)
                                          }
                                lines.append(line)
                    create_log_line(cr,uid,id,object,lines)
                return res
            if fct_src.__name__ in ('unlink'):
                res_ids=args[0]
                old_values={}
                for res_id in res_ids:
                    old_values[res_id]=self.pool.get(object.model).read(cr,uid,res_id,[])

                for res_id in res_ids:
                    if not len(logged_uids) or uid in logged_uids:
                        id=self.pool.get('audittrail.log').create(cr, uid, {"method": fct_src.__name__, "object_id": object.id, "user_id": uid, "res_id": res_id,"name": "%s %s %s" % (fct_src.__name__, object.id, time.strftime("%Y-%m-%d %H:%M:%S"))})
                        lines=[]
                        for field in old_values[res_id]:
                            if old_values[res_id][field]:
                                line={
                                      'name':field,
                                      'old_value':old_values[res_id][field],
                                      'old_value_text':get_value_text(cr,uid,field,old_values[res_id][field],object)
                                      }
                                lines.append(line)
                        create_log_line(cr,uid,id,object,lines)
                res =fct_src( cr, uid,*args, **args2)
                return res

        return my_fct

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
        self.write(cr, uid, ids, {"state": "draft"})
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
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

