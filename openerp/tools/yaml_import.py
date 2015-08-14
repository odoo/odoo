# -*- coding: utf-8 -*-
import threading
import types
import time # used to eval time.strftime expressions
from datetime import datetime, timedelta
import logging

import openerp
import openerp.sql_db as sql_db
import openerp.workflow
import misc
from config import config
import yaml_tag
import yaml
import re
from lxml import etree
from openerp import SUPERUSER_ID

# YAML import needs both safe and unsafe eval, but let's
# default to /safe/.
unsafe_eval = eval
from safe_eval import safe_eval as eval

import assertion_report

_logger = logging.getLogger(__name__)

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

def is_workflow(node):
    return isinstance(node, yaml_tag.Workflow)

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
        self.pool = openerp.registry(cr.dbname)
        self.uid = 1
        self.context = {} # opererp context
        self.eval_context = {'ref': self._ref(),
                             '_ref': self._ref(), # added '_ref' so that record['ref'] is possible
                             'time': time,
                             'datetime': datetime,
                             'timedelta': timedelta}
        self.env = openerp.api.Environment(self.cr, self.uid, self.context)

    def _log(self, *args, **kwargs):
        _logger.log(self.loglevel, *args, **kwargs)

    def _ref(self):
        return lambda xml_id: self.get_id(xml_id)

    def get_model(self, model_name):
        return self.pool[model_name]

    def validate_xml_id(self, xml_id):
        id = xml_id
        if '.' in xml_id:
            module, id = xml_id.split('.', 1)
            assert '.' not in id, "The ID reference '%s' must contains maximum one dot.\n" \
                                  "It is used to refer to other modules ID, in the form: module.record_id" \
                                  % (xml_id,)
            if module != self.module:
                module_count = self.pool['ir.module.module'].search_count(self.cr, self.uid, \
                        ['&', ('name', '=', module), ('state', 'in', ['installed'])])
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
            if '.' in xml_id:
                module, checked_xml_id = xml_id.split('.', 1)
            else:
                module = self.module
                checked_xml_id = xml_id
            try:
                _, id = self.pool['ir.model.data'].get_object_reference(self.cr, self.uid, module, checked_xml_id)
                self.id_map[xml_id] = id
            except ValueError:
                raise ValueError("""%s not found when processing %s.
    This Yaml file appears to depend on missing data. This often happens for
    tests that belong to a module's test suite and depend on each other.""" % (checked_xml_id, self.filename))

        return id

    def get_record(self, xml_id):
        if '.' not in xml_id:
            xml_id = "%s.%s" % (self.module, xml_id)
        return self.env.ref(xml_id)

    def get_context(self, node, eval_dict):
        context = self.context.copy()
        if node.context:
            context.update(eval(node.context, eval_dict))
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
            q = eval(assertion.search, self.eval_context)
            ids = self.pool[assertion.model].search(self.cr, self.uid, q, context=assertion.context)
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
        model = self.get_model(assertion.model)
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
            for id in ids:
                record = model.browse(self.cr, self.uid, id, context)
                for test in expressions:
                    try:
                        success = unsafe_eval(test, self.eval_context, RecordDictWrapper(record))
                    except Exception, e:
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
                                except Exception, e:
                                    lmsg = '<exc>'

                                try:
                                    rmsg = unsafe_eval(right, self.eval_context, RecordDictWrapper(record))
                                except Exception, e:
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
        model = self.get_model(record.model)
        context = self.get_context(record, self.eval_context)
        record_dict = self._create_record(model, fields)
        id_new = model.create(self.cr, self.uid, record_dict, context=context)
        self.id_map[record.id] = int(id_new)
        return record_dict

    def process_record(self, node):
        record, fields = node.items()[0]
        model = self.get_model(record.model)

        view_id = record.view
        if view_id and (view_id is not True) and isinstance(view_id, basestring):
            module = self.module
            if '.' in view_id:
                module, view_id = view_id.split('.',1)
            view_id = self.pool['ir.model.data'].get_object_reference(self.cr, SUPERUSER_ID, module, view_id)[1]

        if model.is_transient():
            record_dict=self.create_osv_memory_record(record, fields)
        else:
            self.validate_xml_id(record.id)
            try:
                self.pool['ir.model.data']._get_id(self.cr, SUPERUSER_ID, self.module, record.id)
                default = False
            except ValueError:
                default = True

            if self.isnoupdate(record) and self.mode != 'init':
                id = self.pool['ir.model.data']._update_dummy(self.cr, SUPERUSER_ID, record.model, self.module, record.id)
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
            view_info = False
            if view_id:
                varg = view_id
                if view_id is True: varg = False
                view_info = model.fields_view_get(self.cr, SUPERUSER_ID, varg, 'form', context)

            record_dict = self._create_record(model, fields, view_info, default=default)
            id = self.pool['ir.model.data']._update(self.cr, SUPERUSER_ID, record.model, \
                    self.module, record_dict, record.id, noupdate=self.isnoupdate(record), mode=self.mode, context=context)
            self.id_map[record.id] = int(id)
            if config.get('import_partial'):
                self.cr.commit()

    def _create_record(self, model, fields, view_info=None, parent={}, default=True):
        """This function processes the !record tag in yalm files. It simulates the record creation through an xml
            view (either specified on the !record tag or the default one for this object), including the calls to
            on_change() functions, and sending only values for fields that aren't set as readonly.
            :param model: model instance
            :param fields: dictonary mapping the field names and their values
            :param view_info: result of fields_view_get() called on the object
            :param parent: dictionary containing the values already computed for the parent, in case of one2many fields
            :param default: if True, the default values must be processed too or not
            :return: dictionary mapping the field names and their values, ready to use when calling the create() function
            :rtype: dict
        """
        def _get_right_one2many_view(fg, field_name, view_type):
            one2many_view = fg[field_name]['views'].get(view_type)
            # if the view is not defined inline, we call fields_view_get()
            if not one2many_view:
                one2many_view = self.pool[fg[field_name]['relation']].fields_view_get(self.cr, SUPERUSER_ID, False, view_type, self.context)
            return one2many_view

        def process_val(key, val):
            if fg[key]['type'] == 'many2one':
                if type(val) in (tuple,list):
                    val = val[0]
            elif fg[key]['type'] == 'one2many':
                if val and isinstance(val, (list,tuple)) and isinstance(val[0], dict):
                    # we want to return only the fields that aren't readonly
                    # For that, we need to first get the right tree view to consider for the field `key´
                    one2many_tree_view = _get_right_one2many_view(fg, key, 'tree')
                    arch = etree.fromstring(one2many_tree_view['arch'].encode('utf-8'))
                    for rec in val:
                        # make a copy for the iteration, as we will alter `rec´
                        rec_copy = rec.copy()
                        for field_key in rec_copy:
                            # if field is missing in view or has a readonly modifier, drop it
                            field_elem = arch.xpath("//field[@name='%s']" % field_key)
                            if field_elem and (field_elem[0].get('modifiers', '{}').find('"readonly": true') >= 0):
                                # TODO: currently we only support if readonly is True in the modifiers. Some improvement may be done in 
                                # order to support also modifiers that look like {"readonly": [["state", "not in", ["draft", "confirm"]]]}
                                del rec[field_key]
                    # now that unwanted values have been removed from val, we can encapsulate it in a tuple as returned value
                    val = map(lambda x: (0,0,x), val)
            elif fg[key]['type'] == 'many2many':
                if val and isinstance(val,(list,tuple)) and isinstance(val[0], (int,long)):
                    val = [(6,0,val)]

            # we want to return only the fields that aren't readonly
            if el.get('modifiers', '{}').find('"readonly": true') >= 0:
                # TODO: currently we only support if readonly is True in the modifiers. Some improvement may be done in 
                # order to support also modifiers that look like {"readonly": [["state", "not in", ["draft", "confirm"]]]}
                return False

            return val

        if view_info:
            arch = etree.fromstring(view_info['arch'].decode('utf-8'))
            view = arch if len(arch) else False
        else:
            view = False
        fields = fields or {}
        if view is not False:
            fg = view_info['fields']
            onchange_spec = model._onchange_spec(self.cr, SUPERUSER_ID, view_info, context=self.context)
            # gather the default values on the object. (Can't use `fields´ as parameter instead of {} because we may
            # have references like `base.main_company´ in the yaml file and it's not compatible with the function)
            defaults = default and model._add_missing_default_values(self.cr, self.uid, {}, context=self.context) or {}

            # copy the default values in record_dict, only if they are in the view (because that's what the client does)
            # the other default values will be added later on by the create().
            record_dict = dict([(key, val) for key, val in defaults.items() if key in fg])

            # Process all on_change calls
            nodes = [view]
            while nodes:
                el = nodes.pop(0)
                if el.tag=='field':
                    field_name = el.attrib['name']
                    assert field_name in fg, "The field '%s' is defined in the form view but not on the object '%s'!" % (field_name, model._name)
                    if field_name in fields:
                        one2many_form_view = None
                        if (view is not False) and (fg[field_name]['type']=='one2many'):
                            # for one2many fields, we want to eval them using the inline form view defined on the parent
                            one2many_form_view = _get_right_one2many_view(fg, field_name, 'form')

                        field_value = self._eval_field(model, field_name, fields[field_name], one2many_form_view or view_info, parent=record_dict, default=default)

                        #call process_val to not update record_dict if values were given for readonly fields
                        val = process_val(field_name, field_value)
                        if val:
                            record_dict[field_name] = val
                        #if (field_name in defaults) and defaults[field_name] == field_value:
                        #    print '*** You can remove these lines:', field_name, field_value

                    #if field_name has a default value or a value is given in the yaml file, we must call its on_change()
                    elif field_name not in defaults:
                        continue

                    if not el.attrib.get('on_change', False):
                        continue

                    if el.attrib['on_change'] in ('1', 'true'):
                        # New-style on_change
                        recs = model.browse(self.cr, SUPERUSER_ID, [], self.context)
                        result = recs.onchange(record_dict, field_name, onchange_spec)

                    else:
                        match = re.match("([a-z_1-9A-Z]+)\((.*)\)", el.attrib['on_change'], re.DOTALL)
                        assert match, "Unable to parse the on_change '%s'!" % (el.attrib['on_change'], )

                        # creating the context
                        class parent2(object):
                            def __init__(self, d):
                                self.d = d
                            def __getattr__(self, name):
                                return self.d.get(name, False)

                        ctx = record_dict.copy()
                        ctx['context'] = self.context
                        ctx['uid'] = SUPERUSER_ID
                        ctx['parent'] = parent2(parent)
                        for a in fg:
                            if a not in ctx:
                                ctx[a] = process_val(a, defaults.get(a, False))

                        # Evaluation args
                        args = map(lambda x: eval(x, ctx), match.group(2).split(','))
                        result = getattr(model, match.group(1))(self.cr, self.uid, [], *args)

                    for key, val in (result or {}).get('value', {}).items():
                        if key in fg:
                            if key not in fields:
                                # do not shadow values explicitly set in yaml.
                                record_dict[key] = process_val(key, val)
                        else:
                            _logger.debug("The returning field '%s' from your on_change call '%s'"
                                            " does not exist either on the object '%s', either in"
                                            " the view '%s'",
                                            key, match.group(1), model._name, view_info['name'])
                else:
                    nodes = list(el) + nodes
        else:
            record_dict = {}

        for field_name, expression in fields.items():
            if field_name in record_dict:
                continue
            field_value = self._eval_field(model, field_name, expression, default=False)
            record_dict[field_name] = field_value
        return record_dict

    def process_ref(self, node, field=None):
        assert node.search or node.id, '!ref node should have a `search` attribute or `id` attribute'
        if node.search:
            if node.model:
                model_name = node.model
            elif field:
                model_name = field.comodel_name
            else:
                raise YamlImportException('You need to give a model for the search, or a field to infer it.')
            model = self.get_model(model_name)
            q = eval(node.search, self.eval_context)
            ids = model.search(self.cr, self.uid, q)
            if node.use:
                instances = model.browse(self.cr, self.uid, ids)
                value = [inst[node.use] for inst in instances]
            else:
                value = ids
        elif node.id:
            value = self.get_id(node.id)
        else:
            value = None
        return value

    def process_eval(self, node):
        return eval(node.expression, self.eval_context)

    def _eval_field(self, model, field_name, expression, view_info=False, parent={}, default=True):
        # TODO this should be refactored as something like model.get_field() in bin/osv
        if field_name not in model._fields:
            raise KeyError("Object '%s' does not contain field '%s'" % (model, field_name))
        field = model._fields[field_name]

        if is_ref(expression):
            elements = self.process_ref(expression, field)
            if field.type in ("many2many", "one2many"):
                value = [(6, 0, elements)]
            else: # many2one
                if isinstance(elements, (list,tuple)):
                    value = self._get_first_result(elements)
                else:
                    value = elements
        elif field.type == "many2one":
            value = self.get_id(expression)
        elif field.type == "one2many":
            other_model = self.get_model(field.comodel_name)
            value = [(0, 0, self._create_record(other_model, fields, view_info, parent, default=default)) for fields in expression]
        elif field.type == "many2many":
            ids = [self.get_id(xml_id) for xml_id in expression]
            value = [(6, 0, ids)]
        elif field.type == "date" and is_string(expression):
            # enforce ISO format for string date values, to be locale-agnostic during tests
            time.strptime(expression, misc.DEFAULT_SERVER_DATE_FORMAT)
            value = expression
        elif field.type == "datetime" and is_string(expression):
            # enforce ISO format for string datetime values, to be locale-agnostic during tests
            time.strptime(expression, misc.DEFAULT_SERVER_DATETIME_FORMAT)
            value = expression
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
        self.env = openerp.api.Environment(self.cr, self.uid, self.context)

    def process_python(self, node):
        python, statements = node.items()[0]
        assert python.model or python.id, "!python node must have attribute `model` or `id`"
        if python.id is None:
            record = self.pool[python.model]
        elif isinstance(python.id, basestring):
            record = self.get_record(python.id)
        else:
            record = self.env[python.model].browse(python.id)
        if python.model:
            assert record._name == python.model, "`id` is not consistent with `model`"
        statements = "\n" * python.first_line + statements.replace("\r\n", "\n")
        code_context = {
            'self': record,
            'model': record._model,
            'cr': self.cr,
            'uid': self.uid,
            'log': self._log,
            'context': self.context,
            'openerp': openerp,
        }
        try:
            code_obj = compile(statements, self.filename, 'exec')
            unsafe_eval(code_obj, {'ref': self.get_id}, code_context)
        except AssertionError, e:
            self._log_assert_failure('AssertionError in Python code %s (line %d): %s',
                python.name, python.first_line, e)
            return
        except Exception, e:
            _logger.debug('Exception during evaluation of !python block in yaml_file %s.', self.filename, exc_info=True)
            raise
        else:
            self.assertion_report.record_success()

    def process_workflow(self, node):
        workflow, values = node.items()[0]
        if self.isnoupdate(workflow) and self.mode != 'init':
            return
        if workflow.ref:
            id = self.get_id(workflow.ref)
        else:
            if not values:
                raise YamlImportException('You must define a child node if you do not give a ref.')
            if not len(values) == 1:
                raise YamlImportException('Only one child node is accepted (%d given).' % len(values))
            value = values[0]
            if not 'model' in value and (not 'eval' in value or not 'search' in value):
                raise YamlImportException('You must provide a "model" and an "eval" or "search" to evaluate.')
            value_model = self.get_model(value['model'])
            local_context = {'obj': lambda x: value_model.browse(self.cr, self.uid, x, context=self.context)}
            local_context.update(self.id_map)
            id = eval(value['eval'], self.eval_context, local_context)

        if workflow.uid is not None:
            uid = workflow.uid
        else:
            uid = self.uid
        self.cr.execute('select distinct signal, sequence, id from wkf_transition ORDER BY sequence,id')
        signals=[x['signal'] for x in self.cr.dictfetchall()]
        if workflow.action not in signals:
            raise YamlImportException('Incorrect action %s. No such action defined' % workflow.action)
        openerp.workflow.trg_validate(uid, workflow.model, id, workflow.action, self.cr)

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
                param_model = self.get_model(param.get('model', model))
                if 'search' in param:
                    q = eval(param['search'], self.eval_context)
                    ids = param_model.search(self.cr, self.uid, q)
                    value = self._get_first_result(ids)
                elif 'eval' in param:
                    local_context = {'obj': lambda x: param_model.browse(self.cr, self.uid, x, self.context)}
                    local_context.update(self.id_map)
                    value = eval(param['eval'], self.eval_context, local_context)
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
        model = self.get_model(function.model)
        if function.eval:
            args = self.process_eval(function.eval)
        else:
            args = self._eval_params(function.model, params)
        method = function.name
        getattr(model, method)(self.cr, self.uid, *args)

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
            action_type = node.type or 'act_window'
            icons = {
                "act_window": 'STOCK_NEW',
                "report.xml": 'STOCK_PASTE',
                "wizard": 'STOCK_EXECUTE',
                "url": 'STOCK_JUMP_TO',
            }
            values['icon'] = icons.get(action_type, 'STOCK_NEW')
            if action_type == 'act_window':
                action_id = self.get_id(node.action)
                self.cr.execute('select view_type,view_mode,name,view_id,target from ir_act_window where id=%s', (action_id,))
                ir_act_window_result = self.cr.fetchone()
                assert ir_act_window_result, "No window action defined for this id %s !\n" \
                        "Verify that this is a window action or add a type argument." % (node.action,)
                action_type, action_mode, action_name, view_id, target = ir_act_window_result
                if view_id:
                    self.cr.execute('SELECT type FROM ir_ui_view WHERE id=%s', (view_id,))
                    # TODO guess why action_mode is ir_act_window.view_mode above and ir_ui_view.type here
                    action_mode = self.cr.fetchone()
                self.cr.execute('SELECT view_mode FROM ir_act_window_view WHERE act_window_id=%s ORDER BY sequence LIMIT 1', (action_id,))
                if self.cr.rowcount:
                    action_mode = self.cr.fetchone()
                if action_type == 'tree':
                    values['icon'] = 'STOCK_INDENT'
                elif action_mode and action_mode.startswith('tree'):
                    values['icon'] = 'STOCK_JUSTIFY_FILL'
                elif action_mode and action_mode.startswith('graph'):
                    values['icon'] = 'terp-graph'
                elif action_mode and action_mode.startswith('calendar'):
                    values['icon'] = 'terp-calendar'
                if target == 'new':
                    values['icon'] = 'STOCK_EXECUTE'
                if not values.get('name', False):
                    values['name'] = action_name
            elif action_type == 'wizard':
                action_id = self.get_id(node.action)
                self.cr.execute('select name from ir_act_wizard where id=%s', (action_id,))
                ir_act_wizard_result = self.cr.fetchone()
                if (not values.get('name', False)) and ir_act_wizard_result:
                    values['name'] = ir_act_wizard_result[0]
            else:
                raise YamlImportException("Unsupported type '%s' in menuitem tag." % action_type)
        if node.sequence:
            values['sequence'] = node.sequence
        if node.icon:
            values['icon'] = node.icon

        self._set_group_values(node, values)

        pid = self.pool['ir.model.data']._update(self.cr, SUPERUSER_ID, \
                'ir.ui.menu', self.module, values, node.id, mode=self.mode, \
                noupdate=self.isnoupdate(node), res_id=res and res[0] or False)

        if node.id and parent_id:
            self.id_map[node.id] = int(parent_id)

        if node.action and pid:
            action_type = node.type or 'act_window'
            action_id = self.get_id(node.action)
            action = "ir.actions.%s,%d" % (action_type, action_id)
            self.pool['ir.model.data'].ir_set(self.cr, SUPERUSER_ID, 'action', \
                    'tree_but_open', 'Menuitem', [('ir.ui.menu', int(parent_id))], action, True, True, xml_id=node.id)

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
        context = eval(str(node.context), self.eval_context)
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
            'auto_refresh': node.auto_refresh,
            'multi': getattr(node, 'multi', False),
        }

        self._set_group_values(node, values)

        if node.target:
            values['target'] = node.target
        id = self.pool['ir.model.data']._update(self.cr, SUPERUSER_ID, \
                'ir.actions.act_window', self.module, values, node.id, mode=self.mode)
        self.id_map[node.id] = int(id)

        if node.src_model:
            keyword = 'client_action_relate'
            value = 'ir.actions.act_window,%s' % id
            replace = node.replace or True
            self.pool['ir.model.data'].ir_set(self.cr, SUPERUSER_ID, 'action', keyword, \
                    node.id, [node.src_model], value, replace=replace, noupdate=self.isnoupdate(node), isobject=True, xml_id=node.id)
        # TODO add remove ir.model.data

    def process_delete(self, node):
        assert getattr(node, 'model'), "Attribute %s of delete tag is empty !" % ('model',)
        if node.model in self.pool:
            if node.search:
                ids = self.pool[node.model].search(self.cr, self.uid, eval(node.search, self.eval_context))
            else:
                ids = [self.get_id(node.id)]
            if len(ids):
                self.pool[node.model].unlink(self.cr, self.uid, ids)
        else:
            self._log("Record not deleted.")

    def process_url(self, node):
        self.validate_xml_id(node.id)

        res = {'name': node.name, 'url': node.url, 'target': node.target}

        id = self.pool['ir.model.data']._update(self.cr, SUPERUSER_ID, \
                "ir.actions.act_url", self.module, res, node.id, mode=self.mode)
        self.id_map[node.id] = int(id)
        # ir_set
        if (not node.menu or eval(node.menu)) and id:
            keyword = node.keyword or 'client_action_multi'
            value = 'ir.actions.act_url,%s' % id
            replace = node.replace or True
            self.pool['ir.model.data'].ir_set(self.cr, SUPERUSER_ID, 'action', \
                    keyword, node.url, ["ir.actions.act_url"], value, replace=replace, \
                    noupdate=self.isnoupdate(node), isobject=True, xml_id=node.id)

    def process_ir_set(self, node):
        if not self.mode == 'init':
            return False
        _, fields = node.items()[0]
        res = {}
        for fieldname, expression in fields.items():
            if is_eval(expression):
                value = eval(expression.expression, self.eval_context)
            else:
                value = expression
            res[fieldname] = value
        self.pool['ir.model.data'].ir_set(self.cr, SUPERUSER_ID, res['key'], res['key2'], \
                res['name'], res['models'], res['value'], replace=res.get('replace',True), \
                isobject=res.get('isobject', False), meta=res.get('meta',None))

    def process_report(self, node):
        values = {}
        for dest, f in (('name','string'), ('model','model'), ('report_name','name')):
            values[dest] = getattr(node, f)
            assert values[dest], "Attribute %s of report is empty !" % (f,)
        for field,dest in (('rml','report_rml'),('file','report_rml'),('xml','report_xml'),('xsl','report_xsl'),('attachment','attachment'),('attachment_use','attachment_use')):
            if getattr(node, field):
                values[dest] = getattr(node, field)
        if node.auto:
            values['auto'] = eval(node.auto)
        if node.sxw:
            sxw_file = misc.file_open(node.sxw)
            try:
                sxw_content = sxw_file.read()
                values['report_sxw_content'] = sxw_content
            finally:
                sxw_file.close()
        if node.header:
            values['header'] = eval(node.header)
        values['multi'] = node.multi and eval(node.multi)
        xml_id = node.id
        self.validate_xml_id(xml_id)

        self._set_group_values(node, values)

        id = self.pool['ir.model.data']._update(self.cr, SUPERUSER_ID, "ir.actions.report.xml", \
                self.module, values, xml_id, noupdate=self.isnoupdate(node), mode=self.mode)
        self.id_map[xml_id] = int(id)

        if not node.menu or eval(node.menu):
            keyword = node.keyword or 'client_print_multi'
            value = 'ir.actions.report.xml,%s' % id
            replace = node.replace or True
            self.pool['ir.model.data'].ir_set(self.cr, SUPERUSER_ID, 'action', \
                    keyword, values['name'], [values['model']], value, replace=replace, isobject=True, xml_id=xml_id)

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
            except Exception, e:
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
        elif is_workflow(node):
            if isinstance(node, types.DictionaryType):
                self.process_workflow(node)
            else:
                self.process_workflow({node: []})
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

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
