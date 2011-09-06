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
        for line in lines:
            field_obj = obj_pool._all_columns.get(line['name'])
            assert field_obj, _("'%s' field does not exist in '%s' model" %(line['name'], model.model))
            field_obj = field_obj.column
            old_value = line.get('old_value', '')
            new_value = line.get('new_value', '')
            old_value_text = line.get('old_value_text', '')
            new_value_text = line.get('new_value_text', '')
            search_models = [ model.id ]
            if obj_pool._inherits:
                search_models += model_pool.search(cr, uid, [('model', 'in', obj_pool._inherits.keys())])
            field_id = field_pool.search(cr, uid, [('name', '=', line['name']), ('model_id', 'in', search_models)])
            if old_value_text == new_value_text:
                continue
            if field_obj._type == 'many2one':
                old_value = old_value and old_value[0] or old_value
                new_value = new_value and new_value[0] or new_value
            vals = {
                    "log_id": log_id,
                    "field_id": field_id and field_id[0] or False,
                    "old_value": old_value,
                    "new_value": new_value,
                    "old_value_text": old_value_text,
                    "new_value_text": new_value_text,
                    "field_description": field_obj.string
                    }
            line_id = log_line_pool.create(cr, uid, vals)
            cr.commit()
        return True

    def get_x2m_m2o_values(self, cr, db, uid, pool, resource_pool, method, field, value, recursive=True):
        field_obj = (resource_pool._all_columns.get(field)).column
        if field_obj._type in ('one2many','many2many'):
            if recursive:
                self.log_fct(db, uid, field_obj._obj, method, None, value, 'child_relation_log')
            data = pool.get(field_obj._obj).name_get(cr, uid, value)
            return map(lambda x:x[1], data)
        elif field_obj._type == 'many2one':
            return value and value[1] or value
        return False
    
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
        pool = pooler.get_pool(db)
        cr = pooler.get_db(db).cursor()
        resource_pool = pool.get(model)
        log_pool = pool.get('audittrail.log')
        model_pool = pool.get('ir.model')

        model_ids = model_pool.search(cr, uid, [('model', '=', model)])
        model_id = model_ids and model_ids[0] or False
        assert model_id, _("'%s' Model does not exist..." %(model))
        model = model_pool.browse(cr, uid, model_id)
        relational_table_log = args and args[-1] == 'child_relation_log' or  False
        if method in ('create'):
            fields_to_read = []
            if relational_table_log:
                res_id = args[0]
            else:
                res_id = fct_src(db, uid_orig, model.model, method, *args)
                cr.commit()
                fields_to_read = args[0].keys()
            resource = resource_pool.read(cr, uid, res_id, fields_to_read)
            if not isinstance(resource, list):
                resource = [resource]
            vals = { 'method': method, 'object_id': model.id,'user_id': uid_orig}
            for resource_data in resource:
                vals.update({'res_id': resource_data['id']})
                del resource_data['id']
                log_id = log_pool.create(cr, uid, vals)
                lines = []
                for field in resource_data:
                    if field in ('__last_update', 'id'):continue
                    ret_val = self.get_x2m_m2o_values(cr, db, uid, pool, resource_pool, method, field, resource_data[field])
                    line = {
                          'name': field,
                          'new_value': resource_data[field],
                          'new_value_text': ret_val and ret_val or resource_data[field]
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
            map(lambda x:old_values.setdefault(x['id'], x), res)
            vals = {'method': method,'object_id': model.id,'user_id': uid_orig}
            for res_id in old_values:
                vals.update({'res_id': res_id})
                log_id = log_pool.create(cr, uid, vals)
                lines = []
                for field in old_values[res_id]:
                    if field in ('__last_update', 'id'):continue
                    ret_val = self.get_x2m_m2o_values(cr, db, uid, pool, resource_pool, method, field, old_values[res_id][field], False)
                    line = {
                          'name': field,
                          'old_value': old_values[res_id][field],
                          'old_value_text': ret_val and ret_val or old_values[res_id][field]
                          }
                    lines.append(line)
                self.create_log_line(cr, uid, log_id, model, lines)
            cr.commit()
            cr.close()
            return res

        elif method in ('unlink'):
            res_ids = args[0]
            res = False
            old_values = {}
            for res_id in res_ids:
                old_values[res_id] = resource_pool.read(cr, uid, res_id)
            vals = {'method': method,'object_id': model.id,'user_id': uid_orig}
            for res_id in res_ids:
                vals.update({'res_id': res_id})
                log_id = log_pool.create(cr, uid, vals)
                lines = []
                for field in old_values[res_id]:
                    if field in ('__last_update', 'id'):continue
                    ret_val = self.get_x2m_m2o_values(cr, db, uid, pool, resource_pool, method, field, old_values[res_id][field])
                    line = {
                          'name': field,
                          'old_value': old_values[res_id][field],
                          'old_value_text': ret_val and ret_val or old_values[res_id][field]
                          }
                    lines.append(line)
                self.create_log_line(cr, uid, log_id, model, lines)
            if not relational_table_log:
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
                if len(args) > 1 and isinstance(args[1], dict):
                    fields = args[1].keys()
                if isinstance(res_ids, (long, int)):
                    res_ids = [res_ids]
            if res_ids:
                resource_data = resource_pool.read(cr, uid, res_ids)
                for resource in resource_data:
                    resource_id = resource['id']
                    del resource['id']
                    old_values_text = {}
                    old_value = {}
                    for field in resource.keys():
                        if field in ('__last_update', 'id'):continue
                        ret_val = self.get_x2m_m2o_values(cr, db, uid, pool, resource_pool, method, field, resource[field])
                        old_value[field] = resource[field]
                        old_values_text[field] = ret_val and ret_val or resource[field]
                    old_values[resource_id] = {'text':old_values_text, 'value': old_value}
            if not relational_table_log:
                res = fct_src(db, uid_orig, model.model, method, *args)
                cr.commit()
            if res_ids:
                resource_data = resource_pool.read(cr, uid, res_ids)
                vals = {'method': method,'object_id': model.id,'user_id': uid_orig }
                for resource in resource_data:
                    resource_id = resource['id']
                    del resource['id']
                    vals.update({'res_id': resource_id})
                    log_id = log_pool.create(cr, uid, vals)
                    lines = []
                    for field in resource.keys():
                        if field in ('__last_update', 'id'):continue
                        ret_val = self.get_x2m_m2o_values(cr, db, uid, pool, resource_pool, method, field, resource[field], False)
                        line = {
                              'name': field,
                              'new_value': resource[field],
                              'old_value': old_values[resource_id]['value'][field],
                              'new_value_text': ret_val and ret_val or resource[field],
                              'old_value_text': old_values[resource_id]['text'][field]
                              }
                        lines.append(line)
                    self.create_log_line(cr, uid, log_id, model, lines)
                cr.commit()
            cr.close()
            return res
        return True

    def audit_log_call(self, db, uid, model, method, action_type, *args, **argv):
        """
        Overrides Object Proxy execute method
        @param db: the current database
        @param uid: the current user's ID for security checks,
        @param object: Object who's values are being changed
        @param method: get any method and create log
        @param action_type: either 'execute' or 'workflow'
        @return: Returns result as per method of Object proxy
        """
        uid_orig = uid
        uid = 1
        pool = pooler.get_pool(db)
        logged_uids = []
        model_pool = pool.get('ir.model')
        rule_pool = pool.get('audittrail.rule')
        cr = pooler.get_db(db).cursor()
        cr.autocommit(True)
        if action_type == 'execute':
            ignore_methods = ['default_get','read','fields_view_get','fields_get','search',
                              'search_count','name_search','name_get','get','request_get',
                              'get_sc', 'unlink', 'write', 'create']
            fct_src = super(audittrail_objects_proxy, self).execute
        else:
            fct_src = super(audittrail_objects_proxy, self).exec_workflow
        try:
            model_ids = model_pool.search(cr, uid, [('model', '=', model)])
            model_id = model_ids and model_ids[0] or False
            if not ('audittrail.rule' in pool.obj_list()) or not model_id:
                 return fct_src(db, uid_orig, model, method, *args, **argv)
            rule_ids = rule_pool.search(cr, uid, [('object_id', '=', model_id), ('state', '=', 'subscribed')])
            if not rule_ids:
                return fct_src(db, uid_orig, model, method, *args, **argv)
            for model_rule in rule_pool.browse(cr, uid, rule_ids):
                logged_uids += map(lambda x:x.id, model_rule.user_id)
                if not logged_uids or uid in logged_uids:
                    if action_type == 'execute':
                        if method in ('read', 'write', 'create', 'unlink'):
                            if getattr(model_rule, 'log_' + method):
                                return self.log_fct(db, uid_orig, model, method, fct_src, *args)
                        elif method not in ignore_methods:
                            if model_rule.log_action:
                                return self.log_fct(db, uid_orig, model, method, fct_src, *args)
                    else:
                        if model_rule.log_workflow:
                            return self.log_fct(db, uid_orig, model, method, fct_src, *args)
                return fct_src(db, uid_orig, model, method, *args, **argv)
        finally:
            cr.close()

    def execute(self, db, uid, model, method, *args, **argv):
        return self.audit_log_call(db, uid, model, method, 'execute', *args, **argv)

    def exec_workflow(self, db, uid, model, method, *args, **argv):
        return self.audit_log_call(db, uid, model, method, 'workflow', *args, **argv)

audittrail_objects_proxy()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

