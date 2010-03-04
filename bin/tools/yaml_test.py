# -*- encoding: utf-8 -*-
import types
import yaml
import time # used to eval time.strftime expressions
import logging

import pooler
import netsvc

from config import config

logger_channel = 'tests'

class YamlImportException(Exception):
    pass

class YamlImportAbortion(Exception):
    pass

class YamlTag(object):
    """Superclass for constructors of custom tags defined in yaml file."""

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
    def __getitem__(self, key):
        return getattr(self, key)
    def __getattr__(self, attr):
        return None
    def __repr__(self):
        return "<%s %s>" % (self.__class__.__name__, sorted(self.__dict__.items()))

class Assert(YamlTag):
    def __init__(self, model, id, severity=netsvc.LOG_ERROR, string="NONAME", **kwargs):
        self.model = model
        self.id = id
        self.severity = severity
        self.string = string
        super(Assert, self).__init__(**kwargs)
    
class Record(YamlTag):
    def __init__(self, model, id, **kwargs):
        self.model = model
        self.id = id
        super(Record, self).__init__(**kwargs)
    
class Python(YamlTag):
    def __init__(self, model, severity=netsvc.LOG_ERROR, name="NONAME", **kwargs):
        self.model= model
        self.severity = severity
        self.name = name
        super(Python, self).__init__(**kwargs)

class Workflow(YamlTag):
    def __init__(self, model, action, **kwargs):
        self.model = model
        self.action = action
        super(Workflow, self).__init__(**kwargs)

class Context(YamlTag):
    def __init__(self, **kwargs):
        super(Context, self).__init__(**kwargs)

class Eval(YamlTag):
    def __init__(self, expression):
        self.expression = expression
        super(Eval, self).__init__()
    
class Ref(YamlTag):
    def __init__(self, xmlid):
        self.xmlid = xmlid
        super(Ref, self).__init__()

def assert_constructor(loader, node):
    kwargs = loader.construct_mapping(node)
    return Assert(**kwargs)

def record_constructor(loader, node):
    kwargs = loader.construct_mapping(node)
    return Record(**kwargs)

def python_constructor(loader, node):
    kwargs = loader.construct_mapping(node)
    return Python(**kwargs)

def workflow_constructor(loader, node):
    kwargs = loader.construct_mapping(node)
    return Workflow(**kwargs)

def context_constructor(loader, node):
    kwargs = loader.construct_mapping(node)
    return Context(**kwargs)

def eval_constructor(loader, node):
    expression = loader.construct_scalar(node)
    return Eval(expression)
    
def ref_constructor(loader, node):
    xmlid = loader.construct_scalar(node)
    return Ref(xmlid)
        
yaml.add_constructor(u"!assert", assert_constructor)
yaml.add_constructor(u"!record", record_constructor)
yaml.add_constructor(u"!python", python_constructor)
yaml.add_constructor(u"!workflow", workflow_constructor)
yaml.add_constructor(u"!context", context_constructor)
yaml.add_constructor(u"!eval", eval_constructor)
yaml.add_constructor(u"!ref", ref_constructor)

def _is_yaml_mapping(node, tag_constructor):
    value = isinstance(node, types.DictionaryType) \
        and len(node.keys()) == 1 \
        and isinstance(node.keys()[0], tag_constructor)
    return value

def is_comment(node):
    return isinstance(node, types.StringTypes)

def is_assert(node):
    return _is_yaml_mapping(node, Assert)

def is_record(node):
    return _is_yaml_mapping(node, Record)

def is_python(node):
    return _is_yaml_mapping(node, Python)

def is_workflow(node):
    return isinstance(node, Workflow) \
        or _is_yaml_mapping(node, Workflow)

def is_context(node):
    return isinstance(node, Context)

def is_eval(node):
    return isinstance(node, Eval)
    
def is_ref(node):
    return isinstance(node, Ref)


class TestReport(object):
    def __init__(self):
        self._report = {}

    def record(self, success, severity):
        """Records the result of an assertion for the failed/success count.
           Returns success."""

        if severity in self._report:
            self._report[severity][success] += 1
        else:
            self._report[severity] = {success: 1, not success: 0}
        return success

    def __str__(self):
        res = []
        res.append('\nAssertions report:\nLevel\tsuccess\tfailed')
        success = failure = 0
        for severity in self._report:
            res.append("%s\t%s\t%s" % (severity, self._report[severity][True], self._report[severity][False]))
            success += self._report[severity][True]
            failure += self._report[severity][False]
        res.append("total\t%s\t%s" % (success, failure))
        res.append("end of report (%s assertion(s) checked)" % success + failure)
        return "\n".join(res)


class YamlInterpreter(object):
    def __init__(self, cr, module, id_map, mode, filename, noupdate=False):
        self.cr = cr
        self.module = module
        self.id_map = id_map
        self.mode = mode
        self.filename = filename
        self.assert_report = TestReport()
        self.noupdate = noupdate
        self.logger = netsvc.Logger()
        self.pool = pooler.get_pool(cr.dbname)
        self.uid = 1
        self.context = {}

    def _ref(self):
        return lambda xml_id: self.get_id(xml_id)

    def get_model(self, model_name):
        model = self.pool.get(model_name)
        assert model, "The model %s does not exist." % (model_name,)
        return model
    
    def validate_xml_id(self, xml_id):
        id = xml_id
        if '.' in xml_id:
            module, id = xml_id.split('.', 1)
            assert '.' not in id, "The ID reference '%s' must contains maximum one dot.\n" \
                                  "It is used to refer to other modules ID, in the form: module.record_id" \
                                  % (xml_id,)
            if module != self.module:
                module_count = self.pool.get('ir.module.module').search_count(self.cr, self.uid, \
                        ['&', ('name', '=', module), ('state', 'in', ['installed'])])
                assert module_count == 1, """The ID "%s" refers to an uninstalled module""" % (xml_id,)
        if len(id) > 64: # TODO where does 64 come from (DB is 128)? should be a constant or loaded form DB
            self.logger.notifyChannel(logger_channel, netsvc.LOG_ERROR, 'id: %s is to long (max: 64)' % (id,))

    def get_id(self, xml_id):
        if isinstance(xml_id, types.IntType):
            id = xml_id
        elif xml_id in self.id_map:
            id = self.id_map[xml_id]
        else:
            if '.' in xml_id:
                module, xml_id = xml_id.split('.', 1)
            else:
                module = self.module
            ir_id = self.pool.get('ir.model.data')._get_id(self.cr, self.uid, module, xml_id)
            obj = self.pool.get('ir.model.data').read(self.cr, self.uid, ir_id, ['res_id'])
            id = int(obj['res_id'])
            self.id_map[xml_id] = id
        return id
    
    def process_comment(self, node):
        return node

    def _log_assert_failure(self, severity, msg, *args):
        self.assert_report.record(False, severity)
        self.logger.notifyChannel(logger_channel, severity, msg % (args))
        if getattr(logging, severity.upper()) >= config['assert_exit_level']:
            raise YamlImportAbortion('Severe assertion failure (%s), aborting.' % (severity,))
        return

    def _get_assertion_id(self, assertion):
        if assertion.id:
            ids = [self.get_id(assertion.id)]
        elif assertion.search:
            q = eval(assertion.search, {'ref': self._ref})
            ids = self.pool.get(assertion.model).search(self.cr, self.uid, q, context=assertion.context)
        if not ids:
            raise YamlImportException('Nothing to assert: you must give either an id or a search criteria.')
        return ids

    def process_assert(self, node):
        assertion, expressions = node.items()[0]

        model = self.get_model(assertion.model)
        ids = self._get_assertion_id(assertion)
        if assertion.count and len(ids) != assertion.count:
            msg = 'assertion "%s" failed!\n'   \
                  ' Incorrect search count:\n' \
                  ' expected count: %d\n'      \
                  ' obtained count: %d\n'
            args = (assertion.string, assertion.count, len(ids))
            self._log_assert_failure(assertion.severity, msg, *args)
        else:
            test_context = {'ref': self._ref, '_ref': self._ref} # added '_ref' so that record['ref'] is possible
            for id in ids:
                record = model.browse(self.cr, self.uid, id, assertion.context)
                for test in expressions.get('test', ''):
                    success = eval(test, test_context, record)
                    if not success:
                        msg = 'Assertion "%s" FAILED\ntest: %s\n'
                        args = (assertion.string, test)
                        self._log_assert_failure(assertion.severity, msg, *args)
                        return
            else: # all tests were successful for this assertion tag (no break)
                self.assert_report.record(True, assertion.severity)

    def process_record(self, node):
        record, fields = node.items()[0]

        self.validate_xml_id(record.id)
        model = self.get_model(record.model)
        record_dict = self._create_record(model, fields)
        id = self.pool.get('ir.model.data')._update(self.cr, self.uid, record.model, \
                self.module, record_dict, record.id, mode=self.mode)
        self.id_map[record.id] = int(id)
        if config.get('import_partial', False):
            self.cr.commit()
    
    def _create_record(self, model, fields):
        record_dict = {}
        for field_name, expression in fields.items():
            field_value = self._eval_field(model, field_name, expression)
            record_dict[field_name] = field_value
        return record_dict        
    
    def _eval_field(self, model, field_name, expression):
        column = model._columns[field_name]
        if column._type == "many2one":
            value = self.get_id(expression)
        elif column._type == "one2many":
            other_model = self.get_model(column._obj)
            value = [(0, 0, self._create_record(other_model, fields)) for fields in expression]
        elif column._type == "many2many":
            ids = [self.get_id(xml_id) for xml_id in expression]
            value= [(6, 0, ids)]
        else: # scalar field
            if isinstance(expression, Eval):
                value = eval(expression.expression)
            else:
                value = expression
            # raise YamlImportException('Unsupported column "%s" or value %s:%s' % (field_name, type(expression), expression))
        return value
    
    def process_context(self, node):
        self.context = node.__dict__
        if 'uid' in node.__dict__:
            self.uid = self.get_id(node.__dict__['uid'])
    
    def process_python(self, node):
        def log(msg):
            self.logger.notifyChannel(logger_channel, netsvc.LOG_TEST, msg)
        python, statements = node.items()[0]
        model = self.get_model(python.model)
        statements = statements.replace("\r\n", "\n").replace("\n", ";")
        code_context = {'self': model, 'cr': self.cr, 'uid': self.uid, 'log': log, 'context': self.context}
        try:
            code = compile(statements, self.filename, 'exec')
            eval(code, code_context)
        except Exception, e:
            raise YamlImportException(e)
        # TODO log success/failure
    
    def process_workflow(self, node):
        workflow, values = node.items()[0]
        model = self.get_model(workflow.model)
        if workflow.ref:
            id = self.get_id(workflow.ref)
        else:
            if not values:
                raise YamlImportException('You must define a child node if you do not give a ref.')
            if not len(values) == 1:
                raise YamlImportException('Only one child node is accepted (%d given).' % len(values))
            value = values[0]
            if not 'model' in value and not 'eval' in value:
                raise YamlImportException('You must provide a model and an expression to evaluate for the workflow.')
            value_model = self.get_model(value['model'])
            local_context = {'ref': self._ref, '_ref': self._ref}
            local_context['obj'] = lambda x: value_model.browse(self.cr, self.uid, x, context=self.context)
            local_context.update(self.id_map)
            id = eval(value['eval'], local_context)
        
        if workflow.uid is not None:
            uid = workflow.uid
        else:
            uid = self.uid
        wf_service = netsvc.LocalService("workflow")
        wf_service.trg_validate(uid, model, id, workflow.action, self.cr)
    
    def process(self, yaml_string):
        """Processes a Yaml string. Custom tags are interpreted by 'process_' instance methods."""
        
        is_preceded_by_comment = False
        for node in yaml.load(yaml_string):
            is_preceded_by_comment = self._log(node, is_preceded_by_comment)
            try:
                self._process_node(node)
            except YamlImportException, e:
                self.logger.notifyChannel(logger_channel, netsvc.LOG_ERROR, e)
            except YamlImportAbortion, e:
                self.logger.notifyChannel(logger_channel, netsvc.LOG_ERROR, e)
                return
    
    def _process_node(self, node):
        if is_comment(node):
            self.process_comment(node)
        elif is_assert(node):
            self.process_assert(node)
        elif is_record(node):
            self.process_record(node)
        elif is_python(node):
            self.process_python(node)
        elif is_context(node):
            self.process_context(node)
        elif is_workflow(node):
            if isinstance(node, types.DictionaryType):
                self.process_workflow(node)
            else:
                self.process_workflow({node: []})
        else:
            raise YamlImportException("Can not process YAML block: %s" % node)
    
    def _log(self, node, is_preceded_by_comment):
        if is_comment(node):
            is_preceded_by_comment = True
            self.logger.notifyChannel(logger_channel, netsvc.LOG_TEST, node)
        elif not is_preceded_by_comment:
            if isinstance(node, types.DictionaryType):
                k, v = node.items()[0]
                msg = "Creating %s\n with %s" % (k, v)
                self.logger.notifyChannel(logger_channel, netsvc.LOG_TEST, msg)
            else:
                self.logger.notifyChannel(logger_channel, netsvc.LOG_TEST, node)
        else:
            is_preceded_by_comment = False
        return is_preceded_by_comment

def yaml_import(cr, module, yamlfile, idref=None, mode='init', noupdate=False, report=None):
    if idref is None:
        idref = {}
    yaml_string = yamlfile.read()
    yaml_interpreter = YamlInterpreter(cr, module, idref, mode, filename=yamlfile.name, noupdate=noupdate)
    yaml_interpreter.process(yaml_string)

# keeps convention of convert.py
convert_yaml_import = yaml_import

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
