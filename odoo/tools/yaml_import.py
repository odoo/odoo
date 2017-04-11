# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import OrderedDict
from datetime import datetime, timedelta
import logging
import re
import time # used to eval time.strftime expressions
import types

from lxml import etree
import yaml

import odoo
from . import assertion_report
from . import yaml_tag
from .config import config
from .misc import file_open, DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from odoo import SUPERUSER_ID

# YAML import needs both safe and unsafe eval, but let's
# default to /safe/.
unsafe_eval = eval
from .safe_eval import safe_eval

_logger = logging.getLogger(__name__)

def encode(s):
    return s.encode('utf8') if isinstance(s, unicode) else s

class YamlImportException(Exception):
    pass

class YamlImportAbortion(Exception):
    pass

def _is_yaml_mapping(node, tag_constructor):
    value = isinstance(node, types.DictionaryType) \
        and len(node.keys()) == 1 \
        and isinstance(node.keys()[0], tag_constructor)
    return value

def is_comment(node):
    return isinstance(node, types.StringTypes)

def is_assert(node):
    return isinstance(node, yaml_tag.Assert) \
        or _is_yaml_mapping(node, yaml_tag.Assert)

def is_record(node):
    return _is_yaml_mapping(node, yaml_tag.Record)

def is_python(node):
    return _is_yaml_mapping(node, yaml_tag.Python)

def is_menuitem(node):
    return isinstance(node, yaml_tag.Menuitem) \
        or _is_yaml_mapping(node, yaml_tag.Menuitem)

def is_function(node):
    return isinstance(node, yaml_tag.Function) \
        or _is_yaml_mapping(node, yaml_tag.Function)

def is_report(node):
    return isinstance(node, yaml_tag.Report)

def is_act_window(node):
    return isinstance(node, yaml_tag.ActWindow)

def is_delete(node):
    return isinstance(node, yaml_tag.Delete)

def is_context(node):
    return isinstance(node, yaml_tag.Context)

def is_url(node):
    return isinstance(node, yaml_tag.Url)

def is_eval(node):
    return isinstance(node, yaml_tag.Eval)

def is_ref(node):
    return isinstance(node, yaml_tag.Ref) \
        or _is_yaml_mapping(node, yaml_tag.Ref)

def is_ir_set(node):
    return _is_yaml_mapping(node, yaml_tag.IrSet)

def is_string(node):
    return isinstance(node, basestring)

class RecordDictWrapper(dict):
    """
    Used to pass a record as locals in eval:
    records do not strictly behave like dict, so we force them to.
    """
    def __init__(self, record):
        self.record = record
    def __getitem__(self, key):
        if key in self.record:
            return self.record[key]
        return dict.__getitem__(self, key)

class YamlInterpreter(object):
    def __init__(self, cr, module, id_map, mode, filename, report=None, noupdate=False, loglevel=logging.DEBUG):
        self.cr = cr
        self.module = module
        self.id_map = id_map
        self.mode = mode
        self.filename = filename
        if report is None:
            report = assertion_report.assertion_report()
        self.assertion_report = report
        self.noupdate = noupdate
        self.loglevel = loglevel
        self.uid = SUPERUSER_ID
        self.context = {} # opererp context
        self.eval_context = {'ref': self.get_id,
                             '_ref': self.get_id, # added '_ref' so that record['ref'] is possible
                             'time': time,
                             'datetime': datetime,
                             'timedelta': timedelta}
        self.env = odoo.api.Environment(self.cr, self.uid, self.context)
        self.sudo_env = self.env

    def _log(self, *args, **kwargs):
        _logger.log(self.loglevel, *args, **kwargs)

    def validate_xml_id(self, xml_id):
        id = xml_id
        if '.' in xml_id:
            module, id = xml_id.split('.', 1)
            assert '.' not in id, "The ID reference '%s' must contain at most one dot.\n" \
                                  "It is used to refer to other modules ID, in the form: module.record_id" \
                                  % (xml_id,)
            if module != self.module:
                module_count = self.env['ir.module.module'].search_count([('name', '=', module), ('state', '=', 'installed')])
                assert module_count == 1, 'The ID "%s" refers to an uninstalled module.' % (xml_id,)
        if len(id) > 64: # TODO where does 64 come from (DB is 128)? should be a constant or loaded form DB
            _logger.error('id: %s is to long (max: 64)', id)

    def get_id(self, xml_id):
        if xml_id is False or xml_id is None:
            return False
        #if not xml_id:
        #    raise YamlImportException("The xml_id should be a non empty string.")
        elif isinstance(xml_id, types.IntType):
            id = xml_id
        elif xml_id in self.id_map:
            id = self.id_map[xml_id]
        else:
            full_xml_id = xml_id
            if '.' not in full_xml_id:
                full_xml_id = self.module + '.' + full_xml_id
            try:
                id = self.env.ref(full_xml_id).id
                self.id_map[xml_id] = id
            except ValueError:
                raise ValueError("""%r not found when processing %s.
    This Yaml file appears to depend on missing data. This often happens for
    tests that belong to a module's test suite and depend on each other.""" % (xml_id, self.filename))

        return id

    def get_record(self, xml_id):
        if '.' not in xml_id:
            xml_id = "%s.%s" % (self.module, xml_id)
        return self.env.ref(xml_id)

    def get_context(self, node, eval_dict):
        context = self.context.copy()
        if node.context:
            context.update(safe_eval(node.context, eval_dict))
        return context

    def isnoupdate(self, node):
        return self.noupdate or node.noupdate or False

    def _get_first_result(self, results, default=False):
        if len(results):
            value = results[0]
            if isinstance(value, types.TupleType):
                value = value[0]
        else:
            value = default
        return value

    def process_comment(self, node):
        return node

    def _log_assert_failure(self, msg, *args):
        self.assertion_report.record_failure()
        _logger.error(msg, *args)

    def _get_assertion_id(self, assertion):
        if assertion.id:
            ids = [self.get_id(assertion.id)]
        elif assertion.search:
            q = safe_eval(assertion.search, self.eval_context)
            ids = self.env(context=assertion.context)[assertion.model].search(q)
        else:
            raise YamlImportException('Nothing to assert: you must give either an id or a search criteria.')
        return ids

    def process_assert(self, node):
        if isinstance(node, dict):
            assertion, expressions = node.items()[0]
        else:
            assertion, expressions = node, []

        if self.isnoupdate(assertion) and self.mode != 'init':
            _logger.warning('This assertion was not evaluated ("%s").', assertion.string)
            return
        model = self.env[assertion.model]
        ids = self._get_assertion_id(assertion)
        if assertion.count is not None and len(ids) != assertion.count:
            msg = 'assertion "%s" failed!\n'   \
                  ' Incorrect search count:\n' \
                  ' expected count: %d\n'      \
                  ' obtained count: %d\n'
            args = (assertion.string, assertion.count, len(ids))
            self._log_assert_failure(msg, *args)
        else:
            context = self.get_context(assertion, self.eval_context)
            records = model.with_context(context).browse(ids)
            for record in records:
                for test in expressions:
                    try:
                        success = unsafe_eval(test, self.eval_context, RecordDictWrapper(record))
                    except Exception as e:
                        _logger.debug('Exception during evaluation of !assert block in yaml_file %s.', self.filename, exc_info=True)
                        raise YamlImportAbortion(e)
                    if not success:
                        msg = 'Assertion "%s" FAILED\ntest: %s\n'
                        args = (assertion.string, test)
                        for aop in ('==', '!=', '<>', 'in', 'not in', '>=', '<=', '>', '<'):
                            if aop in test:
                                left, right = test.split(aop,1)
                                lmsg = ''
                                rmsg = ''
                                try:
                                    lmsg = unsafe_eval(left, self.eval_context, RecordDictWrapper(record))
                                except Exception as e:
                                    lmsg = '<exc>'

                                try:
                                    rmsg = unsafe_eval(right, self.eval_context, RecordDictWrapper(record))
                                except Exception as e:
                                    rmsg = '<exc>'

                                msg += 'values: ! %s %s %s'
                                args += ( lmsg, aop, rmsg )
                                break

                        self._log_assert_failure(msg, *args)
                        return
            else: # all tests were successful for this assertion tag (no break)
                self.assertion_report.record_success()

    def _coerce_bool(self, value, default=False):
        if isinstance(value, types.BooleanType):
            b = value
        if isinstance(value, types.StringTypes):
            b = value.strip().lower() not in ('0', 'false', 'off', 'no')
        elif isinstance(value, types.IntType):
            b = bool(value)
        else:
            b = default
        return b

    def create_osv_memory_record(self, record, fields):
        model = self.env[record.model]
        context = self.get_context(record, self.eval_context)
        record_dict = self._create_record(model, fields, context=context)
        id_new = model.with_context(context).create(record_dict).id
        self.id_map[record.id] = int(id_new)
        return record_dict

    def process_record(self, node):
        record, fields = node.items()[0]
        model = self.env[record.model]
        view_id = record.view
        if view_id and (view_id is not True) and isinstance(view_id, basestring):
            if '.' not in view_id:
                view_id = self.module + '.' + view_id
            view_id = self.env.ref(view_id).id

        if model.is_transient():
            record_dict=self.create_osv_memory_record(record, fields)
        else:
            self.validate_xml_id(record.id)
            module = self.module
            record_id = record.id
            if '.' in record_id:
                module, record_id = record_id.split('.',1)
            try:
                self.sudo_env['ir.model.data']._get_id(module, record_id)
                default = False
            except ValueError:
                default = True

            if self.isnoupdate(record) and self.mode != 'init':
                id = self.sudo_env['ir.model.data']._update_dummy(record.model, module, record_id)
                # check if the resource already existed at the last update
                if id:
                    self.id_map[record] = int(id)
                    return None
                else:
                    if not self._coerce_bool(record.forcecreate):
                        return None

            #context = self.get_context(record, self.eval_context)
            # FIXME: record.context like {'withoutemployee':True} should pass from self.eval_context. example: test_project.yml in project module
            # TODO: cleaner way to avoid resetting password in auth_signup (makes user creation costly)
            context = dict(record.context or {}, no_reset_password=True)
            env = self.env(user=SUPERUSER_ID, context=context)
            view_info = False
            if view_id:
                varg = view_id
                if view_id is True: varg = False
                view_info = model.with_env(env).fields_view_get(varg, 'form')

            record_dict = self._create_record(model, fields, view_info, default=default, context=context)
            id = env['ir.model.data']._update(record.model, \
                    module, record_dict, record_id, noupdate=self.isnoupdate(record), mode=self.mode)
            self.id_map[record.id] = int(id)
            if config.get('import_partial'):
                self.cr.commit()

    def _create_record(self, model, fields, view_info=None, parent={}, default=True, context=None):
        """This function processes the !record tag in yaml files. It simulates the record creation through an xml
            view (either specified on the !record tag or the default one for this object), including the calls to
            on_change() functions, and sending only values for fields that aren't set as readonly.
            :param model: model instance (new API)
            :param fields: dictonary mapping the field names and their values
            :param view_info: result of fields_view_get() called on the object
            :param parent: dictionary containing the values already computed for the parent, in case of one2many fields
            :param default: if True, the default values must be processed too or not
            :return: dictionary mapping the field names and their values, ready to use when calling the create() function
            :rtype: dict
        """
        readonly_re = re.compile(r"""("readonly"|'readonly'): *true""")

        class dotdict(object):
            """ Dictionary class that allow to access a dictionary value by using '.'.
                This is needed to eval correctly statements like 'parent.fieldname' in context.
            """
            def __init__(self, d):
                self._dict = d
            def __getattr__(self, attr):
                return self._dict.get(attr, False)

        def get_field_elems(view):
            """ return the field elements from a view as an OrderedDict """
            def traverse(node, elems):
                if node.tag == 'field':
                    elems[node.get('name')] = node
                else:
                    for child in node:
                        traverse(child, elems)

            elems = OrderedDict()
            traverse(etree.fromstring(encode(view['arch'])), elems)
            return elems

        def is_readonly(field_elem):
            """ return whether a given field is readonly """
            # TODO: currently we only support if readonly is True in modifiers.
            # Some improvement may be done in order to support modifiers like
            # {"readonly": [["state", "not in", ["draft", "confirm"]]]}
            return readonly_re.search(field_elem.get('modifiers', '{}'))

        def get_2many_view(fg, field_name, view_type):
            """ return a view of the given type for the given field's comodel """
            fdesc = fg[field_name]
            return fdesc['views'].get(view_type) or \
                   self.sudo_env[fdesc['relation']].fields_view_get(False, view_type)

        def process_vals(fg, vals):
            """ sanitize the given field values """
            result = {}
            for field_name, field_value in vals.iteritems():
                if field_name not in fg:
                    continue
                if fg[field_name]['type'] == 'many2one' and isinstance(field_value, (tuple, list)):
                    field_value = field_value[0]
                elif fg[field_name]['type'] in ('one2many', 'many2many'):
                    # 2many fields: sanitize field values of sub-records
                    sub_fg = get_2many_view(fg, field_name, 'form')['fields']
                    def process(command):
                        if isinstance(command, (tuple, list)) and command[0] in (0, 1):
                            return (command[0], command[1], process_vals(sub_fg, command[2]))
                        elif isinstance(command, dict):
                            return process_vals(sub_fg, command)
                        return command
                    field_value = map(process, field_value or [])
                result[field_name] = field_value
            return result

        def post_process(fg, elems, vals):
            """ filter out readonly fields from vals """
            result = {}
            for field_name, field_value in vals.iteritems():
                if is_readonly(elems[field_name]):
                    continue
                if fg[field_name]['type'] in ('one2many', 'many2many'):
                    # 2many fields: filter field values of sub-records
                    sub_view = get_2many_view(fg, field_name, 'form')
                    sub_fg = sub_view['fields']
                    sub_elems = get_field_elems(sub_view)
                    def process(command):
                        if isinstance(command, (tuple, list)) and command[0] in (0, 1):
                            return (command[0], command[1], post_process(sub_fg, sub_elems, command[2]))
                        elif isinstance(command, dict):
                            return (0, 0, post_process(sub_fg, sub_elems, command))
                        return command
                    field_value = map(process, field_value or [])
                result[field_name] = field_value
            return result

        context = context or {}
        fields = fields or {}
        parent_values = {context['field_parent']: parent} if context.get('field_parent') else {}

        if view_info:
            fg = view_info['fields']
            elems = get_field_elems(view_info)
            recs = model.sudo().with_context(**context)
            onchange_spec = recs._onchange_spec(view_info)
            record_dict = {}

            if default:
                # gather the default values on the object. (Can't use `fields´ as parameter instead of {} because we may
                # have references like `base.main_company´ in the yaml file and it's not compatible with the function)
                defaults = recs.sudo(self.uid)._add_missing_default_values({})

                # copy the default values in record_dict, only if they are in the view (because that's what the client does)
                # the other default values will be added later on by the create(). The other fields in the view that haven't any
                # default value are set to False because we may have references to them in other field's context
                record_dict = dict.fromkeys(fg, False)
                record_dict.update(process_vals(fg, defaults))

                # execute onchange on default values first
                default_names = [name for name in elems if name in record_dict]
                result = recs.onchange(dict(record_dict, **parent_values), default_names, onchange_spec)
                record_dict.update(process_vals(fg, result.get('value', {})))

            # fill in fields, and execute onchange where necessary
            for field_name, field_elem in elems.iteritems():
                assert field_name in fg, "The field '%s' is defined in the form view but not on the object '%s'!" % (field_name, model._name)
                if is_readonly(field_elem):
                    # skip readonly fields
                    continue

                if field_name not in fields:
                    continue

                ctx = dict(context)
                form_view = view_info
                if fg[field_name]['type'] == 'one2many':
                    # evaluate one2many fields using the inline form view defined in the parent
                    form_view = get_2many_view(fg, field_name, 'form')
                    ctx['field_parent'] = fg[field_name]['relation_field']
                if default and field_elem.get('context'):
                    ctx.update(safe_eval(field_elem.get('context'),
                                         globals_dict={'parent': dotdict(parent)},
                                         locals_dict=record_dict))

                field_value = self._eval_field(model, field_name, fields[field_name], form_view, parent=record_dict, default=default, context=ctx)
                record_dict.update(process_vals(fg, {field_name: field_value}))

                # if field_name is given or has a default value, we evaluate its onchanges
                if not field_elem.attrib.get('on_change', False):
                    continue

                result = recs.onchange(dict(record_dict, **parent_values), field_name, onchange_spec)
                record_dict.update(process_vals(fg, {
                    key: val
                    for key, val in result.get('value', {}).iteritems()
                    if key not in fields        # do not shadow values explicitly set in yaml
                }))

            record_dict = post_process(fg, elems, record_dict)

        else:
            record_dict = {}

        for field_name, expression in fields.iteritems():
            if record_dict.get(field_name):
                continue
            field_value = self._eval_field(model, field_name, expression, parent=record_dict, default=False, context=context)
            record_dict[field_name] = field_value

        # filter returned values; indeed the last modification in the import process have added a default
        # value for all fields in the view; however some fields present in the view are not stored and
        # should not be sent to create. This bug appears with not stored function fields in the new API.
        return {
            key: val
            for key, val in record_dict.iteritems()
            for field in [model._fields[key].base_field]
            if field.store or field.inverse
        }

    def process_ref(self, node, field=None):
        assert node.search or node.id, '!ref node should have a `search` attribute or `id` attribute'
        if node.search:
            if node.model:
                model_name = node.model
            elif field:
                model_name = field.comodel_name
            else:
                raise YamlImportException('You need to give a model for the search, or a field to infer it.')
            model = self.env[model_name]
            q = safe_eval(node.search, self.eval_context)
            instances = model.search(q)
            if node.use:
                value = [inst[node.use] for inst in instances]
            else:
                value = instances.ids
        elif node.id:
            if field and field.type == 'reference':
                record = self.get_record(node.id)
                value = "%s,%s" % (record._name, record.id)
            else:
                value = self.get_id(node.id)
        else:
            value = None
        return value

    def process_eval(self, node):
        return safe_eval(node.expression, self.eval_context)

    def _eval_field(self, model, field_name, expression, view_info=False, parent={}, default=True, context=None):
        # TODO this should be refactored as something like model.get_field() in bin/osv
        if field_name not in model._fields:
            raise KeyError("Object '%s' does not contain field '%s'" % (model, field_name))
        field = model._fields[field_name]

        if is_ref(expression):
            elements = self.process_ref(expression, field)
            if field.type in ("many2many", "one2many"):
                value = [(6, 0, elements)]
            else: # many2one or reference
                if isinstance(elements, (list,tuple)):
                    value = self._get_first_result(elements)
                else:
                    value = elements
        elif field.type == "many2one":
            value = self.get_id(expression)
        elif field.type == "one2many":
            comodel = self.env[field.comodel_name]
            value = [(0, 0, self._create_record(comodel, fields, view_info, parent=parent, default=default, context=context)) for fields in expression]
        elif field.type == "many2many":
            ids = [self.get_id(xml_id) for xml_id in expression]
            value = [(6, 0, ids)]
        elif field.type == "date" and is_string(expression):
            # enforce ISO format for string date values, to be locale-agnostic during tests
            time.strptime(expression, DEFAULT_SERVER_DATE_FORMAT)
            value = expression
        elif field.type == "datetime" and is_string(expression):
            # enforce ISO format for string datetime values, to be locale-agnostic during tests
            time.strptime(expression, DEFAULT_SERVER_DATETIME_FORMAT)
            value = expression
        elif field.type == "reference":
            record = self.get_record(expression)
            value = "%s,%s" % (record._name, record.id)
        else: # scalar field
            if is_eval(expression):
                value = self.process_eval(expression)
            else:
                value = expression
            # raise YamlImportException('Unsupported field "%s" or value %s:%s' % (field_name, type(expression), expression))
        return value

    def process_context(self, node):
        self.context = node.__dict__
        if node.uid:
            self.uid = self.get_id(node.uid)
        if node.noupdate:
            self.noupdate = node.noupdate
        self.env = odoo.api.Environment(self.cr, self.uid, self.context)
        self.sudo_env = self.env(user=SUPERUSER_ID)

    def process_python(self, node):
        python, statements = node.items()[0]
        assert python.model or python.id, "!python node must have attribute `model` or `id`"
        if python.id is None:
            record = self.env[python.model]
        elif isinstance(python.id, basestring):
            record = self.get_record(python.id)
        else:
            record = self.env[python.model].browse(python.id)
        if python.model:
            assert record._name == python.model, "`id` is not consistent with `model`"
        statements = "\n" * python.first_line + statements.replace("\r\n", "\n")
        code_context = {
            'self': record,
            'model': record,
            'cr': self.cr,
            'uid': self.uid,
            'log': self._log,
            'context': self.context,
            'openerp': odoo,
        }
        try:
            code_obj = compile(statements, self.filename, 'exec')
            unsafe_eval(code_obj, {'ref': self.get_id}, code_context)
        except AssertionError as e:
            self._log_assert_failure('AssertionError in Python code %s (line %d): %s',
                python.name, python.first_line, e)
            return
        except Exception as e:
            _logger.debug('Exception during evaluation of !python block in yaml_file %s.', self.filename, exc_info=True)
            raise
        else:
            self.assertion_report.record_success()

    def _eval_params(self, model, params):
        args = []
        for i, param in enumerate(params):
            if isinstance(param, types.ListType):
                value = self._eval_params(model, param)
            elif is_ref(param):
                value = self.process_ref(param)
            elif is_eval(param):
                value = self.process_eval(param)
            elif isinstance(param, types.DictionaryType): # supports XML syntax
                param_model = self.env[param.get('model', model)]
                if 'search' in param:
                    q = safe_eval(param['search'], self.eval_context)
                    ids = param_model.search(q).ids
                    value = self._get_first_result(ids)
                elif 'eval' in param:
                    local_context = {'obj': param_model.browse}
                    local_context.update(self.id_map)
                    value = safe_eval(param['eval'], self.eval_context, local_context)
                else:
                    raise YamlImportException('You must provide either a !ref or at least a "eval" or a "search" to function parameter #%d.' % i)
            else:
                value = param # scalar value
            args.append(value)
        return args

    def process_function(self, node):
        function, params = node.items()[0]
        if self.isnoupdate(function) and self.mode != 'init':
            return
        model = self.env[function.model]
        if function.eval:
            args = self.process_eval(function.eval)
        else:
            args = self._eval_params(function.model, params)
        # this one still depends on the old API
        return odoo.api.call_kw(model, function.name, args, {})

    def _set_group_values(self, node, values):
        if node.groups:
            group_names = node.groups.split(',')
            groups_value = []
            for group in group_names:
                if group.startswith('-'):
                    group_id = self.get_id(group[1:])
                    groups_value.append((3, group_id))
                else:
                    group_id = self.get_id(group)
                    groups_value.append((4, group_id))
            values['groups_id'] = groups_value

    def process_menuitem(self, node):
        self.validate_xml_id(node.id)

        if not node.parent:
            parent_id = False
            self.cr.execute('select id from ir_ui_menu where parent_id is null and name=%s', (node.name,))
            res = self.cr.fetchone()
            values = {'parent_id': parent_id, 'name': node.name}
        else:
            parent_id = self.get_id(node.parent)
            values = {'parent_id': parent_id}
            if node.name:
                values['name'] = node.name
            try:
                res = [ self.get_id(node.id) ]
            except: # which exception ?
                res = None

        if node.action:
            action = self.get_record(node.action)
            values['action'] = '%s,%s' % (action._name, action.id)
            if not values.get('name'):
                values['name'] = action.name

        if node.sequence:
            values['sequence'] = node.sequence

        self._set_group_values(node, values)

        pid = self.sudo_env['ir.model.data']._update('ir.ui.menu', self.module, values, node.id, \
                mode=self.mode, noupdate=self.isnoupdate(node), res_id=res and res[0] or False)

        if node.id and pid:
            self.id_map[node.id] = int(pid)

    def process_act_window(self, node):
        assert getattr(node, 'id'), "Attribute %s of act_window is empty !" % ('id',)
        assert getattr(node, 'name'), "Attribute %s of act_window is empty !" % ('name',)
        assert getattr(node, 'res_model'), "Attribute %s of act_window is empty !" % ('res_model',)
        self.validate_xml_id(node.id)
        view_id = False
        if node.view:
            view_id = self.get_id(node.view)
        if not node.context:
            node.context={}
        context = safe_eval(str(node.context), self.eval_context)
        values = {
            'name': node.name,
            'type': node.type or 'ir.actions.act_window',
            'view_id': view_id,
            'domain': node.domain,
            'context': context,
            'res_model': node.res_model,
            'src_model': node.src_model,
            'view_type': node.view_type or 'form',
            'view_mode': node.view_mode or 'tree,form',
            'usage': node.usage,
            'limit': node.limit,
            'multi': getattr(node, 'multi', False),
        }

        self._set_group_values(node, values)

        if node.target:
            values['target'] = node.target
        id = self.sudo_env['ir.model.data']._update('ir.actions.act_window', self.module, values, node.id, mode=self.mode)
        self.id_map[node.id] = int(id)

        if node.src_model:
            keyword = 'client_action_relate'
            value = 'ir.actions.act_window,%s' % id
            res_id = False
            model = node.src_model
            if isinstance(model, (list, tuple)):
                model, res_id = model
            self.env['ir.values'].sudo().set_action(node.id, action_slot=keyword, model=model, action=value, res_id=res_id)
        # TODO add remove ir.model.data

    def process_delete(self, node):
        assert getattr(node, 'model'), "Attribute %s of delete tag is empty !" % ('model',)
        if node.model in self.env:
            if node.search:
                records = self.env[node.model].search(safe_eval(node.search, self.eval_context))
            else:
                records = self.env[node.model].browse(self.get_id(node.id))
            if records:
                records.unlink()
        else:
            self._log("Record not deleted.")

    def process_url(self, node):
        self.validate_xml_id(node.id)

        res = {'name': node.name, 'url': node.url, 'target': node.target}

        id = self.sudo_env['ir.model.data']._update("ir.actions.act_url", self.module, res, node.id, mode=self.mode)
        self.id_map[node.id] = int(id)
        # ir_set
        if (not node.menu or safe_eval(node.menu)) and id:
            keyword = node.keyword or 'client_action_multi'
            value = 'ir.actions.act_url,%s' % id
            self.env['ir.values'].sudo().set_action(node.url, action_slot=keyword, model="ir.actions.act_url", action=value, res_id=False)

    def process_ir_set(self, node):
        if not self.mode == 'init':
            return False
        _, fields = node.items()[0]
        res = {}
        for fieldname, expression in fields.items():
            if is_eval(expression):
                value = safe_eval(expression.expression, self.eval_context)
            else:
                value = expression
            res[fieldname] = value
        ir_values = self.env['ir.values']
        for model in res['models']:
            res_id = False
            if isinstance(model, (list, tuple)):
                model, res_id = model
            if res['key'] == 'default':
                ir_values.sudo().set_default(model, field_name=res['name'], value=res['value'], condition=res['key2'])
            elif res['key'] == 'action':
                ir_values.sudo().set_action(res['name'], action_slot=res['key2'], model=model, action=res['value'], res_id=res_id)

    def process_report(self, node):
        values = {}
        for dest, f in (('name','string'), ('model','model'), ('report_name','name')):
            values[dest] = getattr(node, f)
            assert values[dest], "Attribute %s of report is empty !" % (f,)
        for field,dest in (('rml','report_rml'),('file','report_rml'),('xml','report_xml'),('xsl','report_xsl'),('attachment','attachment'),('attachment_use','attachment_use')):
            if getattr(node, field):
                values[dest] = getattr(node, field)
        if node.auto:
            values['auto'] = safe_eval(node.auto)
        if node.sxw:
            sxw_file = file_open(node.sxw)
            try:
                sxw_content = sxw_file.read()
                values['report_sxw_content'] = sxw_content
            finally:
                sxw_file.close()
        if node.header:
            values['header'] = safe_eval(node.header)
        values['multi'] = node.multi and safe_eval(node.multi)
        xml_id = node.id
        self.validate_xml_id(xml_id)

        self._set_group_values(node, values)

        id = self.sudo_env['ir.model.data']._update("ir.actions.report.xml", \
                self.module, values, xml_id, noupdate=self.isnoupdate(node), mode=self.mode)
        self.id_map[xml_id] = int(id)

        if not node.menu or safe_eval(node.menu):
            keyword = node.keyword or 'client_print_multi'
            value = 'ir.actions.report.xml,%s' % id
            ir_values = self.env['ir.values']
            res_id = False
            model = values['model']
            if isinstance(model, (list, tuple)):
                model, res_id = model
            ir_values.sudo().set_action(values['name'], action_slot=keyword, model=model, action=value, res_id=res_id)

    def process_none(self):
        """
        Empty node or commented node should not pass silently.
        """
        self._log_assert_failure("You have an empty block in your tests.")


    def process(self, yaml_string):
        """
        Processes a Yaml string. Custom tags are interpreted by 'process_' instance methods.
        """
        yaml_tag.add_constructors()

        is_preceded_by_comment = False
        for node in yaml.load(yaml_string):
            is_preceded_by_comment = self._log_node(node, is_preceded_by_comment)
            try:
                self._process_node(node)
            except Exception as e:
                _logger.exception(e)
                raise

    def _process_node(self, node):
        if is_comment(node):
            self.process_comment(node)
        elif is_assert(node):
            self.process_assert(node)
        elif is_record(node):
            self.process_record(node)
        elif is_python(node):
            self.process_python(node)
        elif is_menuitem(node):
            self.process_menuitem(node)
        elif is_delete(node):
            self.process_delete(node)
        elif is_url(node):
            self.process_url(node)
        elif is_context(node):
            self.process_context(node)
        elif is_ir_set(node):
            self.process_ir_set(node)
        elif is_act_window(node):
            self.process_act_window(node)
        elif is_report(node):
            self.process_report(node)
        elif is_function(node):
            if isinstance(node, types.DictionaryType):
                self.process_function(node)
            else:
                self.process_function({node: []})
        elif node is None:
            self.process_none()
        else:
            raise YamlImportException("Can not process YAML block: %s" % node)

    def _log_node(self, node, is_preceded_by_comment):
        if is_comment(node):
            is_preceded_by_comment = True
            self._log(node)
        elif not is_preceded_by_comment:
            if isinstance(node, types.DictionaryType):
                msg = "Creating %s\n with %s"
                args = node.items()[0]
                self._log(msg, *args)
            else:
                self._log(node)
        else:
            is_preceded_by_comment = False
        return is_preceded_by_comment

def yaml_import(cr, module, yamlfile, kind, idref=None, mode='init', noupdate=False, report=None):
    if idref is None:
        idref = {}
    loglevel = logging.DEBUG
    yaml_string = yamlfile.read()
    yaml_interpreter = YamlInterpreter(cr, module, idref, mode, filename=yamlfile.name, report=report, noupdate=noupdate, loglevel=loglevel)
    yaml_interpreter.process(yaml_string)

# keeps convention of convert.py
convert_yaml_import = yaml_import
