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

from osv import fields, osv
from osv.osv import object_proxy
from tools.translate import _
import pooler
import time
import tools

class audittrail_rule(osv.osv):
    """
    For Auddittrail Rule
    """
    _name = 'audittrail.rule'
    _description = "Audittrail Rule"
    _columns = {
        "name": fields.char("Rule Name", size=32, required=True),
        "object_id": fields.many2one('ir.model', 'Object', required=True, help="Select object for which you want to generate log."),
        "user_id": fields.many2many('res.users', 'audittail_rules_users',
                                            'user_id', 'rule_id', 'Users', help="if  User is not added then it will applicable for all users"),
        "log_read": fields.boolean("Log Reads", help="Select this if you want to keep track of read/open on any record of the object of this rule"),
        "log_write": fields.boolean("Log Writes", help="Select this if you want to keep track of modification on any record of the object of this rule"),
        "log_unlink": fields.boolean("Log Deletes", help="Select this if you want to keep track of deletion on any record of the object of this rule"),
        "log_create": fields.boolean("Log Creates",help="Select this if you want to keep track of creation on any record of the object of this rule"),
        "log_action": fields.boolean("Log Action",help="Select this if you want to keep track of actions on the object of this rule"),
        "log_workflow": fields.boolean("Log Workflow",help="Select this if you want to keep track of workflow on any record of the object of this rule"),
        "state": fields.selection((("draft", "Draft"),
                                   ("subscribed", "Subscribed")),
                                   "State", required=True),
        "action_id": fields.many2one('ir.actions.act_window', "Action ID"),

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
        """
        Subscribe Rule for auditing changes on object and apply shortcut for logs on that object.
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of Auddittrail Rule’s IDs.
        @return: True
        """
        obj_action = self.pool.get('ir.actions.act_window')
        obj_model = self.pool.get('ir.model.data')
        #start Loop
        for thisrule in self.browse(cr, uid, ids):
            obj = self.pool.get(thisrule.object_id.model)
            if not obj:
                raise osv.except_osv(
                        _('WARNING: audittrail is not part of the pool'),
                        _('Change audittrail depends -- Setting rule as DRAFT'))
                self.write(cr, uid, [thisrule.id], {"state": "draft"})
            val = {
                 "name": 'View Log',
                 "res_model": 'audittrail.log',
                 "src_model": thisrule.object_id.model,
                 "domain": "[('object_id','=', " + str(thisrule.object_id.id) + "), ('res_id', '=', active_id)]"

            }
            action_id = obj_action.create(cr, uid, val)
            self.write(cr, uid, [thisrule.id], {"state": "subscribed", "action_id": action_id})
            keyword = 'client_action_relate'
            value = 'ir.actions.act_window,' + str(action_id)
            res = obj_model.ir_set(cr, uid, 'action', keyword, 'View_log_' + thisrule.object_id.model, [thisrule.object_id.model], value, replace=True, isobject=True, xml_id=False)
            #End Loop
        return True

    def unsubscribe(self, cr, uid, ids, *args):
        """
        Unsubscribe Auditing Rule on object
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of Auddittrail Rule’s IDs.
        @return: True
        """
        obj_action = self.pool.get('ir.actions.act_window')
        ir_values_obj = self.pool.get('ir.values')
        value=''
        #start Loop
        for thisrule in self.browse(cr, uid, ids):
            if thisrule.id in self.__functions:
                for function in self.__functions[thisrule.id]:
                    setattr(function[0], function[1], function[2])
            w_id = obj_action.search(cr, uid, [('name', '=', 'View Log'), ('res_model', '=', 'audittrail.log'), ('src_model', '=', thisrule.object_id.model)])
            if w_id:
                obj_action.unlink(cr, uid, w_id)
                value = "ir.actions.act_window" + ',' + str(w_id[0])
            val_id = ir_values_obj.search(cr, uid, [('model', '=', thisrule.object_id.model), ('value', '=', value)])
            if val_id:
                ir_values_obj = pooler.get_pool(cr.dbname).get('ir.values')
                res = ir_values_obj.unlink(cr, uid, [val_id[0]])
            self.write(cr, uid, [thisrule.id], {"state": "draft"})
        #End Loop
        return True

audittrail_rule()


class audittrail_log(osv.osv):
    """
    For Audittrail Log
    """
    _name = 'audittrail.log'
    _description = "Audittrail Log"

    def _name_get_resname(self, cr, uid, ids, *args):
        data = {}
        for resname in self.browse(cr, uid, ids,[]):
            model_object = resname.object_id
            res_id = resname.res_id
            if model_object and res_id:
                model_pool = self.pool.get(model_object.model)
                res = model_pool.read(cr, uid, res_id, ['name'])
                data[resname.id] = res['name']
            else:
                 data[resname.id] = False
        return data

    _columns = {
        "name": fields.char("Resource Name",size=64),
        "object_id": fields.many2one('ir.model', 'Object'),
        "user_id": fields.many2one('res.users', 'User'),
        "method": fields.char("Method", size=64),
        "timestamp": fields.datetime("Date"),
        "res_id": fields.integer('Resource Id'),
        "line_ids": fields.one2many('audittrail.log.line', 'log_id', 'Log lines'),
    }

    _defaults = {
        "timestamp": lambda *a: time.strftime("%Y-%m-%d %H:%M:%S")
    }
    _order = "timestamp desc"

audittrail_log()


class audittrail_log_line(osv.osv):
    """
    Audittrail Log Line.
    """
    _name = 'audittrail.log.line'
    _description = "Log Line"
    _columns = {
          'field_id': fields.many2one('ir.model.fields', 'Fields', required=True),
          'log_id': fields.many2one('audittrail.log', 'Log'),
          'log': fields.integer("Log ID"),
          'old_value': fields.text("Old Value"),
          'new_value': fields.text("New Value"),
          'old_value_text': fields.text('Old value Text'),
          'new_value_text': fields.text('New value Text'),
          'field_description': fields.char('Field Description', size=64),
        }

audittrail_log_line()


class audittrail_objects_proxy(object_proxy):
    """ Uses Object proxy for auditing changes on object of subscribed Rules"""

    def get_value_text(self, cr, uid, field_name, values, model, context=None):
        """
        Gets textual values for the fields
        e.g.: For field of type many2one it gives its name value instead of id

        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param field_name: List of fields for text values
        @param values: Values for field to be converted into textual values
        @return: values: List of textual values for given fields
        """
        if not context:
            context = {}
        if field_name in('__last_update','id'):
            return values
        pool = pooler.get_pool(cr.dbname)
        obj_pool = pool.get(model.model)
        field_obj = obj_pool._all_columns.get(field_name, False)
        assert field_obj, _("'%s' field does not exist in '%s' model" %(field_name, model.model))
        field_obj = field_obj.column
        if field_obj._obj:
            relation_model_pool = pool.get(field_obj._obj)
            relational_rec_name = relation_model_pool._rec_name
        if field_obj._type == 'many2one':
            if values and isinstance(values, tuple):
                if values[0]:
                    relation_model_object = relation_model_pool.read(cr, uid, values[0], [relational_rec_name])
                    return relation_model_object.get(relational_rec_name)
            return False
        elif field_obj._type in ('many2many','one2many'):
            data = relation_model_pool.read(cr, uid, values, [relational_rec_name])
            return map(lambda x:x.get(relational_rec_name, False), data)
        return values

    def create_log_line(self, cr, uid, log_id, model, lines=[]):
        """
        Creates lines for changed fields with its old and new values

        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param model: Object who's values are being changed
        @param lines: List of values for line is to be created
        """
        pool = pooler.get_pool(cr.dbname)
        obj_pool = pool.get(model.model)
        model_pool = pool.get('ir.model')
        field_pool = pool.get('ir.model.fields')
        log_line_pool = pool.get('audittrail.log.line')
        #start Loop
        for line in lines:
            if line['name'] in('__last_update','id'):
                continue
            if obj_pool._inherits:
                inherits_ids = model_pool.search(cr, uid, [('model', '=', obj_pool._inherits.keys()[0])])
                field_ids = field_pool.search(cr, uid, [('name', '=', line['name']), ('model_id', 'in', (model.id, inherits_ids[0]))])
            else:
                field_ids = field_pool.search(cr, uid, [('name', '=', line['name']), ('model_id', '=', model.id)])
            field_id = field_ids and field_ids[0] or False
            assert field_id, _("'%s' field does not exist in '%s' model" %(line['name'], model.model))

            field = field_pool.read(cr, uid, field_id)
            old_value = 'old_value' in line and  line['old_value'] or ''
            new_value = 'new_value' in line and  line['new_value'] or ''
            old_value_text = 'old_value_text' in line and  line['old_value_text'] or ''
            new_value_text = 'new_value_text' in line and  line['new_value_text'] or ''

            if old_value_text == new_value_text:
                continue
            if field['ttype'] == 'many2one':
                if type(old_value) == tuple:
                    old_value = old_value[0]
                if type(new_value) == tuple:
                    new_value = new_value[0]
            vals = {
                    "log_id": log_id,
                    "field_id": field_id,
                    "old_value": old_value,
                    "new_value": new_value,
                    "old_value_text": old_value_text,
                    "new_value_text": new_value_text,
                    "field_description": field['field_description']
                    }
            line_id = log_line_pool.create(cr, uid, vals)
            cr.commit()
        #End Loop
        return True


    def log_fct(self, db, uid, model, method, fct_src, *args):
        """
        Logging function: This function is performs logging operations according to method
        @param db: the current database
        @param uid: the current user’s ID for security checks,
        @param object: Object who's values are being changed
        @param method: method to log: create, read, write, unlink
        @param fct_src: execute method of Object proxy

        @return: Returns result as per method of Object proxy
        """
        uid_orig = uid
        uid = 1
        res2 = args
        pool = pooler.get_pool(db)
        cr = pooler.get_db(db).cursor()
        resource_pool = pool.get(model)
        log_pool = pool.get('audittrail.log')
        model_pool = pool.get('ir.model')

        model_ids = model_pool.search(cr, uid, [('model', '=', model)])
        model_id = model_ids and model_ids[0] or False
        assert model_id, _("'%s' Model does not exist..." %(model))
        model = model_pool.browse(cr, uid, model_id)

        if method in ('create'):
            res_id = fct_src(db, uid_orig, model.model, method, *args)
            cr.commit()
            resource = resource_pool.read(cr, uid, res_id, args[0].keys())
            vals = {
                    "method": method,
                    "object_id": model.id,
                    "user_id": uid_orig,
                    "res_id": resource['id'],
            }
            if 'id' in resource:
                del resource['id']
            log_id = log_pool.create(cr, uid, vals)
            lines = []
            for field in resource:
                line = {
                      'name': field,
                      'new_value': resource[field],
                      'new_value_text': self.get_value_text(cr, uid, field, resource[field], model)
                      }
                lines.append(line)
            self.create_log_line(cr, uid, log_id, model, lines)

            cr.commit()
            cr.close()
            return res_id

        elif method in ('read'):
            res_ids = args[0]
            old_values = {}
            res = fct_src(db, uid_orig, model.model, method, *args)
            if type(res) == list:
                for v in res:
                    old_values[v['id']] = v
            else:
                old_values[res['id']] = res
            for res_id in old_values:
                vals = {
                    "method": method,
                    "object_id": model.id,
                    "user_id": uid_orig,
                    "res_id": res_id,

                }
                log_id = log_pool.create(cr, uid, vals)
                lines = []
                for field in old_values[res_id]:
                    line = {
                              'name': field,
                              'old_value': old_values[res_id][field],
                              'old_value_text': self.get_value_text(cr, uid, field, old_values[res_id][field], model)
                              }
                    lines.append(line)

                self.create_log_line(cr, uid, log_id, model, lines)
            cr.commit()
            cr.close()
            return res

        elif method in ('unlink'):
            res_ids = args[0]
            old_values = {}
            for res_id in res_ids:
                old_values[res_id] = resource_pool.read(cr, uid, res_id)

            for res_id in res_ids:
                vals = {
                    "method": method,
                    "object_id": model.id,
                    "user_id": uid_orig,
                    "res_id": res_id,

                }
                log_id = log_pool.create(cr, uid, vals)
                lines = []
                for field in old_values[res_id]:
                    if field in ('id'):
                        continue
                    line = {
                          'name': field,
                          'old_value': old_values[res_id][field],
                          'old_value_text': self.get_value_text(cr, uid, field, old_values[res_id][field], model)
                          }
                    lines.append(line)

                self.create_log_line(cr, uid, log_id, model, lines)
            res = fct_src(db, uid_orig, model.model, method, *args)
            cr.commit()
            cr.close()
            return res
        else:
            res_ids = []
            res = True
            if args:
                res_ids = args[0]
                old_values = {}
                fields = []
                if len(args)>1 and type(args[1]) == dict:
                    fields = args[1].keys()
                if type(res_ids) in (long, int):
                    res_ids = [res_ids]
            if res_ids:
                for resource in resource_pool.read(cr, uid, res_ids):
                    resource_id = resource['id']
                    if 'id' in resource:
                        del resource['id']
                    old_values_text = {}
                    old_value = {}
                    for field in resource.keys():
                        old_value[field] = resource[field]
                        old_values_text[field] = self.get_value_text(cr, uid, field, resource[field], model)
                    old_values[resource_id] = {'text':old_values_text, 'value': old_value}

            res = fct_src(db, uid_orig, model.model, method, *args)
            cr.commit()

            if res_ids:
                for resource in resource_pool.read(cr, uid, res_ids):
                    resource_id = resource['id']
                    if 'id' in resource:
                        del resource['id']
                    vals = {
                        "method": method,
                        "object_id": model.id,
                        "user_id": uid_orig,
                        "res_id": resource_id,
                    }


                    log_id = log_pool.create(cr, uid, vals)
                    lines = []
                    for field in resource.keys():
                        line = {
                              'name': field,
                              'new_value': resource[field],
                              'old_value': old_values[resource_id]['value'][field],
                              'new_value_text': self.get_value_text(cr, uid, field, resource[field], model),
                              'old_value_text': old_values[resource_id]['text'][field]
                              }
                        lines.append(line)

                    self.create_log_line(cr, uid, log_id, model, lines)
                cr.commit()
            cr.close()
            return res
        return True



    def execute(self, db, uid, model, method, *args, **kw):
        """
        Overrides Object Proxy execute method
        @param db: the current database
        @param uid: the current user's ID for security checks,
        @param object: Object who's values are being changed
        @param method: get any method and create log

        @return: Returns result as per method of Object proxy
        """
        uid_orig = uid
        uid = 1
        pool = pooler.get_pool(db)
        model_pool = pool.get('ir.model')
        rule_pool = pool.get('audittrail.rule')
        cr = pooler.get_db(db).cursor()
        cr.autocommit(True)
        logged_uids = []
        ignore_methods = ['default_get','read','fields_view_get','fields_get','search',
                          'search_count','name_search','name_get','get','request_get',
                          'get_sc', 'unlink', 'write', 'create']
        fct_src = super(audittrail_objects_proxy, self).execute
        try:
            model_ids = model_pool.search(cr, uid, [('model', '=', model)])
            model_id = model_ids and model_ids[0] or False
            if not ('audittrail.rule' in pool.obj_list()) or not model_id:
                 return fct_src(db, uid_orig, model, method, *args)
            rule_ids = rule_pool.search(cr, uid, [('object_id', '=', model_id), ('state', '=', 'subscribed')])
            if not rule_ids:
                return fct_src(db, uid_orig, model, method, *args)

            for model_rule in rule_pool.browse(cr, uid, rule_ids):
                logged_uids += map(lambda x:x.id, model_rule.user_id)
                if not logged_uids or uid in logged_uids:
                    if method in ('read', 'write', 'create', 'unlink'):
                        if getattr(model_rule, 'log_' + method):
                            return self.log_fct(db, uid_orig, model, method, fct_src, *args)
                    elif method not in ignore_methods:
                        if model_rule.log_action:
                            return self.log_fct(db, uid_orig, model, method, fct_src, *args)
                return fct_src(db, uid_orig, model, method, *args)
        finally:
            cr.close()

    def exec_workflow(self, db, uid, model, method, *args, **argv):
        uid_orig = uid
        uid = 1

        pool = pooler.get_pool(db)
        logged_uids = []
        fct_src = super(audittrail_objects_proxy, self).exec_workflow
        field = method
        rule = False
        model_pool = pool.get('ir.model')
        rule_pool = pool.get('audittrail.rule')
        cr = pooler.get_db(db).cursor()
        cr.autocommit(True)
        try:
            model_ids = model_pool.search(cr, uid, [('model', '=', model)])
            for obj_name in pool.obj_list():
                if obj_name == 'audittrail.rule':
                    rule = True
            if not rule:
                return super(audittrail_objects_proxy, self).exec_workflow(db, uid_orig, model, method, *args, **argv)
            if not model_ids:
                return super(audittrail_objects_proxy, self).exec_workflow(db, uid_orig, model, method, *args, **argv)

            rule_ids = rule_pool.search(cr, uid, [('object_id', 'in', model_ids), ('state', '=', 'subscribed')])
            if not rule_ids:
                return super(audittrail_objects_proxy, self).exec_workflow(db, uid_orig, model, method, *args, **argv)

            for thisrule in rule_pool.browse(cr, uid, rule_ids):
                for user in thisrule.user_id:
                    logged_uids.append(user.id)
                if not logged_uids or uid in logged_uids:
                    if thisrule.log_workflow:
                        return self.log_fct(db, uid_orig, model, method, fct_src, *args)
                return super(audittrail_objects_proxy, self).exec_workflow(db, uid_orig, model, method, *args, **argv)

            return True
        finally:
            cr.close()

audittrail_objects_proxy()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

