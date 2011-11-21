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
        "state": fields.selection((("draft", "Draft"), ("subscribed", "Subscribed")), "State", required=True),
        "action_id": fields.many2one('ir.actions.act_window', "Action ID"),
    }
    _defaults = {
        'state': 'draft',
        'log_create': 1,
        'log_unlink': 1,
        'log_write': 1,
    }
    _sql_constraints = [
        ('model_uniq', 'unique (object_id)', """There is already a rule defined on this object\n You cannot define another: please edit the existing one.""")
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

class audittrail_objects_proxy(object_proxy):
    """ Uses Object proxy for auditing changes on object of subscribed Rules"""

    def get_value_text(self, cr, uid, pool, resource_pool, method, field, value, recursive=True):
        """
        Gets textual values for the fields. 
            If the field is a many2one, it returns the name. 
            If it's a one2many or a many2many, it returns a list of name. 
            In other cases, it just returns the value.
        :param cr: the current row, from the database cursor,
        :param uid: the current user’s ID for security checks,
        :param pool: current db's pooler object.
        :param resource_pool: pooler object of the model which values are being changed.
        :param field: for which the text value is to be returned.
        :param value: value of the field.
        :param recursive: True or False, True will repeat the process recursively => when?
        :return: string value or a list of values(for O2M/M2M)
        """

        field_obj = (resource_pool._all_columns.get(field)).column
        if field_obj._type in ('one2many','many2many'):
            if recursive:
                self.log_fct(cr, uid, field_obj._obj, method, None, value, 'child_relation_log')
            data = pool.get(field_obj._obj).name_get(cr, uid, value)
            #return the modifications on x2many fields as a list of names
            return map(lambda x:x[1], data)
        elif field_obj._type == 'many2one':
            #return the modifications on a many2one field as its value returned by name_get()
            return value and value[1] or value
        return value

    def create_log_line(self, cr, uid, log_id, model, lines=[]):
        """
        Creates lines for changed fields with its old and new values

        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param model: Object which values are being changed
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
            search_models = [model.id]
            if obj_pool._inherits:
                search_models += model_pool.search(cr, uid, [('model', 'in', obj_pool._inherits.keys())])
            field_id = field_pool.search(cr, uid, [('name', '=', line['name']), ('model_id', 'in', search_models)])
            if field_obj._type == 'many2one':
                old_value = old_value and old_value[0] or old_value
                new_value = new_value and new_value[0] or new_value
            vals = {
                    "log_id": log_id,
                    "field_id": field_id and field_id[0] or False,
                    "old_value": old_value,
                    "new_value": new_value,
                    "old_value_text": line.get('old_value_text', ''),
                    "new_value_text": line.get('new_value_text', ''),
                    "field_description": field_obj.string
                    }
            line_id = log_line_pool.create(cr, uid, vals)
        return True

    def start_log_process(self, cr, user_id, model, method, resource_data, pool, resource_pool):
        """
         Logging function: This function performs the logging operation for create/read/unlink operation
         :param cr: the current row, from the database cursor,
         :param user_id: the current user’s ID,
         :param model: record of ir.model related to the object which values are being changed
         :param method: method to log: create, read, unlink
         :param resource_data: list of data modified for the model
         :param pool: current db's pooler object.
         :param resource_pool: pooler object of the model who's values are being changed.
         :return:True
        """
        #checking if an audittrail rule apply in super admin mode
        if self.check_rules(cr, 1, model.model, method):
            key1 = '%s_value'%(method == 'create' and 'new' or 'old')
            key2 = '%s_value_text'%(method == 'create' and 'new' or 'old')
            vals = {'method': method, 'object_id': model.id,'user_id': user_id}
            for resource, fields in resource_data.iteritems():
                lines = []
                for field_key, value in fields.iteritems():
                    if field_key in ('__last_update', 'id'):continue
                    ret_val = self.get_value_text(cr, 1, pool, resource_pool, method, field_key, value, method != 'read')
                    line = {
                          'name': field_key,
                          key1: value,
                          key2: ret_val and ret_val or value
                          }
                    lines.append(line)
                if lines:
                    vals.update({'res_id': resource})
                    log_id = pool.get('audittrail.log').create(cr, 1, vals)
                    self.create_log_line(cr, 1, log_id, model, lines)
        return True

    def log_fct(self, cr, uid, model, method, fct_src, *args):
        """
        Logging function: This function is performing the logging operation
        @param model: Object whose values are being changed
        @param method: method to log: create, read, write, unlink
        @param fct_src: execute method of Object proxy

        @return: Returns result as per method of Object proxy
        """
        uid_orig = uid
        uid = 1
        pool = pooler.get_pool(cr.dbname)
        resource_pool = pool.get(model)
        model_pool = pool.get('ir.model')
        model_ids = model_pool.search(cr, 1, [('model', '=', model)])
        model_id = model_ids and model_ids[0] or False
        assert model_id, _("'%s' Model does not exist..." %(model))
        model = model_pool.browse(cr, uid, model_id)
        relational_table_log = True if (args and args[-1] == 'child_relation_log') else False

        if method == 'create':
            resource_data = {}
            fields_to_read = []
            if relational_table_log:
                res = args[0]
            else:
                res = fct_src(cr, uid_orig, model.model, method, *args)
                fields_to_read = args[0].keys()
            if res:
                resource = resource_pool.read(cr, uid, res, fields_to_read)
                if not isinstance(resource,list):
                    resource = [resource]
                map(lambda x: resource_data.setdefault(x['id'], x), resource)
                self.start_log_process(cr, uid_orig, model, method, resource_data, pool, resource_pool)

        elif method in('read', 'unlink'):
            res_ids = args[0]
            old_values = {}
            if method == 'read':
                res = fct_src(cr, uid_orig, model.model, method, *args)
                map(lambda x: old_values.setdefault(x['id'], x), res)
            else:
                res = resource_pool.read(cr, uid, res_ids)
                map(lambda x:old_values.setdefault(x['id'], x), res)
            self.start_log_process(cr, uid_orig, model, method, old_values, pool, resource_pool)
            if not relational_table_log and method == 'unlink':
                res = fct_src(cr, uid_orig, model.model, method, *args)
        else: #method is write or workflow action
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
                #store the old values into a dictionary
                old_values = self.get_data(cr, uid_orig, pool, res_ids, model, method)
            #process the original function or workflow trigger
            res = fct_src(cr, uid_orig, model.model, method, *args)
            if method == 'copy':
                res_ids = [res]
            if res_ids:
                #check the new value and store them into a dictionary
                new_values = self.get_data(cr, uid_orig, pool, res_ids, model, method)
                self.process_data(cr, uid_orig, pool, res_ids, model, method, old_values, new_values)
        return res

    def get_data(self, cr, uid_orig, pool, res_ids, model, method):
        """
        This is specially created to log actions and workflow actions on an object recursively.
        It processes and iterates recursively on old data (i.e before the method was executed )
        and stores it in a dict. Then this dict is used to compare with the new data
        (i.e after the method execution) and log the changes.

            :param cr: the current row, from the database cursor,
            :param uid_orig: the current user’s ID,
            :param pool: current db's pooler object.
            :param res_ids: Id's of resource to be logged/compared.
            :param model: Object whose values are being changed
            :param method: method to log: create, read, unlink,write,actions,workflow actions
            :return: dict mapping a tuple (model_id, resource_id) with its value and textual value
                { (model_id, resource_id): { 'value': ...
                                             'textual_value': ...
                                           },
                }
        """
        data = {}
        # read all the fields of the given resource in super admin mode
        resource_pool = pool.get(model.model)
        for resource in resource_pool.read(cr, 1, res_ids):
            values_text = {}
            values = {}
            resource_id = resource['id']
            for field in resource:
                if field in ('__last_update', 'id'):
                    continue
                values[field] = resource[field]
                ret_val = self.get_value_text(cr, 1, pool, resource_pool, method, field, resource[field], False)
                values_text[field] = ret_val and ret_val or resource[field]
                data[(model.id, resource_id)] = {'text':values_text, 'value': values}
                field_obj = resource_pool._all_columns.get(field).column
                if field_obj._type in ('one2many','many2many'):
                    #checking if an audittrail rule apply in super admin mode
                    if self.check_rules(cr, 1, field_obj._obj, method):
                        #checking if the model associated to a *2m field exists, in super admin mode
                        x2m_model_ids = pool.get('ir.model').search(cr, 1, [('model', '=', field_obj._obj)])
                        x2m_model_id = x2m_model_ids and x2m_model_ids[0] or False
                        assert x2m_model_id, _("'%s' Model does not exist..." %(field_obj._obj))
                        x2m_model = pool.get('ir.model').browse(cr, 1, x2m_model_id)
                        data.update(self.get_data(cr, 1, pool, resource[field], x2m_model, method))
        return data

    def prepare_audittrail_log_line(self, cr, uid, pool, model, resource, method, old_values, new_values):
        """
        This function compares the old data (i.e before the method was executed) and the new data 
        (after the method was executed) and returns a structure with all the needed information to
        log those differences.

        :param cr: the current row, from the database cursor,
        :param uid: the current user’s ID,
        :param pool: current db's pooler object.
        :param model: model object which values are being changed
        :param resource: dictionary mapping all the fields of a given resource and its current values
        :param method: method to log: create, read, unlink, write, actions, workflow actions
        :param old_values: dict of values read before execution of the method
        :param new_values: dict of values read after execution of the method

        :return: dictionary with 
            * keys: tuples build as ID of model object to log and ID of resource to log
            * values: list of all the changes in field values for this couple (model, resource)
              return {
                (model.id, resource['id']): []
              }

        The reason why the structure returned is build as above is because when modifying an existing 
        record (res.partner, for example), we may have to log a change done in a x2many field (on 
        res.partner.address, for example)
        """
        key = (model.id, resource['id'])
        lines = {
            key: []
        }
        for field in resource:
            if field in ('__last_update', 'id'):
                continue
            field_obj = (pool.get(model.model)._all_columns.get(field)).column
            if field_obj._type in ('one2many','many2many'):
                # checking if an audittrail rule apply in super admin mode
                if self.check_rules(cr, 1, field_obj._obj, method):
                    # checking if the model associated to a *2m field exists, in super admin mode
                    x2m_model_ids = pool.get('ir.model').search(cr, 1, [('model', '=', field_obj._obj)])
                    x2m_model_id = x2m_model_ids and x2m_model_ids[0] or False
                    assert x2m_model_id, _("'%s' Model does not exist..." %(field_obj._obj))
                    x2m_model = pool.get('ir.model').browse(cr, 1, x2m_model_id)
                    resource_ids = list(set(old_values[(model.id, resource['id'])]['value'][field] + new_values[(model.id, resource['id'])]['value'][field]))
                    if resource_ids:
                        for resource_id in resource_ids:
                            if (x2m_model_id, resource_id) in new_values:
                                x2many_values = new_values[(x2m_model_id, resource_id)]
                            else:
                                x2many_values = old_values[(x2m_model_id, resource_id)]
                            x2many_values['value'].update({'id': resource_id})
                            lines.update(self.prepare_audittrail_log_line(cr, 1, pool, x2m_model, x2many_values['value'], method, old_values, new_values))
            # if the value value is different than the old value: record the change
            if key not in old_values or key not in new_values or old_values[key]['value'][field] != new_values[key]['value'][field]:
                data = {
                      'name': field,
                      'new_value': resource[field],
                      'old_value': key in old_values and old_values[key]['value'].get(field),
                      'new_value_text': key in new_values and new_values[key]['text'].get(field),
                      'old_value_text': key in old_values and old_values[key]['text'].get(field)
                }
                lines[key].append(data)
        return lines

    def process_data(self, cr, uid, pool, res_ids, model, method, old_values={}, new_values={}):
        """
        This function processes and iterates recursively to log the difference between the old
        data (i.e before the method was executed) and the new data and creates audittrail log
        accordingly.

        :param cr: the current row, from the database cursor,
        :param uid: the current user’s ID,
        :param pool: current db's pooler object.
        :param res_ids: Id's of resource to be logged/compared.
        :param model: model object which values are being changed
        :param method: method to log: create, read, unlink, write, actions, workflow actions
        :param old_values: dict of values read before execution of the method
        :param new_values: dict of values read after execution of the method
        :return: True
        """
        # read all the field of the given resource in super admin mode
        for resource in pool.get(model.model).read(cr, 1, res_ids):
            # compare old and new values and get audittrail log lines accordingly
            lines = self.prepare_audittrail_log_line(cr, uid, pool, model, resource, method, old_values, new_values)

            # if at least one modification has been found
            for model_id, resource_id in lines:
                vals = {
                    'method': method,
                    'object_id': model_id,
                    'user_id': uid,
                    'res_id': resource_id,
                }
                if (model_id, resource_id) not in old_values and method !='copy':
                    # the resource was not existing so we are forcing the method to 'create'
                    # (because it could also come with the value 'write' if we are creating
                    #  new record through a one2many field)
                    vals.update({'method': 'create'})
                if (model_id, resource_id) not in new_values and method !='copy':
                    # the resource is not existing anymore so we are forcing the method to 'unlink'
                    # (because it could also come with the value 'write' if we are deleting the
                    #  record through a one2many field)
                    vals.update({'method': 'unlink'})
                # create the audittrail log in super admin mode, only if a change has been detected
                if lines[(model_id, resource_id)]:
                    log_id = pool.get('audittrail.log').create(cr, 1, vals)
                    model = pool.get('ir.model').browse(cr, uid, model_id)
                    self.create_log_line(cr, 1, log_id, model, lines[(model_id, resource_id)])
        return True

    def process_data_old(self, cr, uid_orig, pool, res_ids, model, method, original_values={}, type='new'):
        """
        This is specially created to log actions and workflow actions on an object recursively.
        It processes and iterates recursively on old data (i.e before the method was executed )
        and stores it in a dict. Then this dict is used to compare with the new data
        (i.e after the method execution) and log the changes.

        :param cr: the current row, from the database cursor,
        :param uid_orig: the current user’s ID,
        :param pool: current db's pooler object.
        :param res_ids: Id's of resource to be logged/compared.
        :param model: Object whose values are being changed
        :param method: method to log: create, read, unlink,write,actions,workflow actions
        :param original_values: dict of values of res_ids read before execution of the method only when type is 'new'
        :param type: Either of 'new' or 'old' to know which data to process.
        :return: dict of values
        """
        resource_pool = pool.get(model.model)
        resource_data = resource_pool.read(cr, 1, res_ids)
        _old_values = {}
        for resource in resource_data:
            _old_values_text = {}
            _old_value = {}
            resource_id = resource['id']
            lines = []
            for field in resource:
                if field in ('__last_update', 'id'):continue
                field_obj = (resource_pool._all_columns.get(field)).column
                if field_obj._type in ('one2many','many2many'):
                    #checking if an audittrail rule apply in super admin mode
                    if self.check_rules(cr, 1, field_obj._obj, method):
                        #checking if the model associated to a *2m field exists, in super admin mode
                        x2m_model_ids = pool.get('ir.model').search(cr, 1, [('model', '=', field_obj._obj)])
                        x2m_model_id = x2m_model_ids and x2m_model_ids[0] or False
                        assert x2m_model_id, _("'%s' Model does not exist..." %(field_obj._obj))
                        x2m_model = pool.get('ir.model').browse(cr, 1, x2m_model_id)
                        _old_values[field] = self.process_data(cr, 1, pool, resource[field], x2m_model, method, original_values.get(field,{}), type=type)
                ret_val = self.get_value_text(cr, 1, pool, resource_pool, method, field, resource[field], False)
                if type == 'new':
                    line = {
                              'name': field,
                              'new_value': resource[field],
                              'old_value': resource_id in original_values and original_values[resource_id]['value'].get(field),
                              'new_value_text': ret_val and ret_val or resource[field],
                              'old_value_text': resource_id in original_values and original_values[resource_id]['text'].get(field)
                              }
                    if line.get('new_value_text') != line.get('old_value_text'):
                        lines.append(line)
                else:
                    _old_value[field] = resource[field]
                    _old_values_text[field] = ret_val and ret_val or resource[field]
            if type == 'new':
                if lines:
                    vals = {
                        'method': method,
                        'object_id': model.id,
                        'user_id': uid_orig,
                        'res_id': resource_id,
                    }
                    if resource_id not in original_values and method !='copy':
                        # the resource was not existing so we are forcing the method to 'create'
                        # (because it could also come with the value 'write' if we are creating 
                        #  new record through a one2many field)
                        vals.update({'method': 'create'})
                    # create the audittrail log in super admin mode
                    log_id = pool.get('audittrail.log').create(cr, 1, vals)
                    self.create_log_line(cr, 1, log_id, model, lines)
            else:
                _old_values[resource_id] = {'text':_old_values_text, 'value': _old_value}
        return _old_values

    def check_rules(self, cr, uid, model, method):
        """
        Checks if auditrails is installed for that db and then if one rule match
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID,
        @param model: value of _name of the object which values are being changed
        @param method: method to log: create, read, unlink,write,actions,workflow actions
        @return: True or False
        """
        pool = pooler.get_pool(cr.dbname)
        if 'audittrail.rule' in pool.models:
            model_ids = pool.get('ir.model').search(cr, 1, [('model', '=', model)])
            model_id = model_ids and model_ids[0] or False
            if model_id:
                rule_ids = pool.get('audittrail.rule').search(cr, 1, [('object_id', '=', model_id), ('state', '=', 'subscribed')])
                for rule in pool.get('audittrail.rule').read(cr, 1, rule_ids, ['user_id','log_read','log_write','log_create','log_unlink','log_action','log_workflow']):
                    if len(rule['user_id']) == 0 or uid in rule['user_id']:
                        if rule.get('log_'+method,0):
                            return True
                        elif method not in ('default_get','read','fields_view_get','fields_get','search','search_count','name_search','name_get','get','request_get', 'get_sc', 'unlink', 'write', 'create'):
                            if rule['log_action']:
                                return True

    def execute_cr(self, cr, uid, model, method, *args, **kw):
        fct_src = super(audittrail_objects_proxy, self).execute_cr
        if self.check_rules(cr,uid,model,method):
            return self.log_fct(cr, uid, model, method, fct_src, *args)
        return fct_src(cr, uid, model, method, *args)

    def exec_workflow_cr(self, cr, uid, model, method, *args, **argv):
        fct_src = super(audittrail_objects_proxy, self).exec_workflow_cr
        if self.check_rules(cr,uid,model,'workflow'):
            return self.log_fct(cr, uid, model, method, fct_src, *args)
        return fct_src(cr, uid, model, method, *args)

audittrail_objects_proxy()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

