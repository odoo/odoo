# -*- encoding: utf-8 -*-
import types
import time # used to eval time.strftime expressions
import logging

import pooler
import netsvc
import misc
from config import config
import yaml_tag

import yaml

logger_channel = 'tests'

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
    return _is_yaml_mapping(node, yaml_tag.Assert)

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


class TestReport(object):
    def __init__(self):
        self._report = {}

    def record(self, success, severity):
        """
        Records the result of an assertion for the failed/success count.
        Returns success.
        """
        if severity in self._report:
            self._report[severity][success] += 1
        else:
            self._report[severity] = {success: 1, not success: 0}
        return success

    def __str__(self):
        res = []
        res.append('\nAssertions report:\nLevel\tsuccess\tfailure')
        success = failure = 0
        for severity in self._report:
            res.append("%s\t%s\t%s" % (severity, self._report[severity][True], self._report[severity][False]))
            success += self._report[severity][True]
            failure += self._report[severity][False]
        res.append("total\t%s\t%s" % (success, failure))
        res.append("end of report (%s assertion(s) checked)" % success + failure)
        return "\n".join(res)

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
    def __init__(self, cr, module, id_map, mode, filename, noupdate=False):
        self.cr = cr
        self.module = module
        self.id_map = id_map
        self.mode = mode
        self.filename = filename
        self.assert_report = TestReport()
        self.noupdate = noupdate
        self.logger = logging.getLogger("%s.%s" % (logger_channel, self.module))
        self.pool = pooler.get_pool(cr.dbname)
        self.uid = 1
        self.context = {} # opererp context
        self.eval_context = {'ref': self._ref, '_ref': self._ref, 'time': time} # added '_ref' so that record['ref'] is possible

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
                assert module_count == 1, 'The ID "%s" refers to an uninstalled module.' % (xml_id,)
        if len(id) > 64: # TODO where does 64 come from (DB is 128)? should be a constant or loaded form DB
            self.logger.log(logging.ERROR, 'id: %s is to long (max: 64)', id)

    def get_id(self, xml_id):
        if not xml_id:
            raise YamlImportException("The xml_id should be a non empty string.")
        if isinstance(xml_id, types.IntType):
            id = xml_id
        elif xml_id in self.id_map:
            id = self.id_map[xml_id]
        else:
            if '.' in xml_id:
                module, checked_xml_id = xml_id.split('.', 1)
            else:
                module = self.module
                checked_xml_id = xml_id
            ir_id = self.pool.get('ir.model.data')._get_id(self.cr, self.uid, module, checked_xml_id)
            obj = self.pool.get('ir.model.data').read(self.cr, self.uid, ir_id, ['res_id'])
            id = int(obj['res_id'])
            self.id_map[xml_id] = id
        return id
    
    def get_context(self, node, eval_dict):
        context = self.context.copy()
        if node.context:
            context.update(eval(node.context, eval_dict))
        return context

    def isnoupdate(self, node):
        return self.noupdate or node.noupdate or False
    
    def process_comment(self, node):
        return node

    def _log_assert_failure(self, severity, msg, *args):
        self.assert_report.record(False, severity)
        self.logger.log(severity, msg, *args)
        if severity >= config['assert_exit_level']:
            raise YamlImportAbortion('Severe assertion failure (%s), aborting.' % logging.getLevelName(severity))
        return

    def _get_assertion_id(self, assertion):
        if assertion.id:
            ids = [self.get_id(assertion.id)]
        elif assertion.search:
            q = eval(assertion.search, self.eval_context)
            ids = self.pool.get(assertion.model).search(self.cr, self.uid, q, context=assertion.context)
        if not ids:
            raise YamlImportException('Nothing to assert: you must give either an id or a search criteria.')
        return ids

    def process_assert(self, node):
        assertion, expressions = node.items()[0]

        if self.isnoupdate(assertion) and self.mode != 'init':
            self.logger.warn('This assertion was not evaluated ("%s").' % assertion.string)
            return
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
            context = self.get_context(assertion, self.eval_context)
            for id in ids:
                record = model.browse(self.cr, self.uid, id, context)
                for test in expressions:
                    try:
                        success = eval(test, self.eval_context, RecordDictWrapper(record))
                    except Exception, e:
                        raise YamlImportAbortion(e)
                    if not success:
                        msg = 'Assertion "%s" FAILED\ntest: %s\n'
                        args = (assertion.string, test)
                        self._log_assert_failure(assertion.severity, msg, *args)
                        return
            else: # all tests were successful for this assertion tag (no break)
                self.assert_report.record(True, assertion.severity)

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
    
    def process_record(self, node):
        record, fields = node.items()[0]

        self.validate_xml_id(record.id)
        if self.isnoupdate(record) and self.mode != 'init':
            id = self.pool.get('ir.model.data')._update_dummy(self.cr, self.uid, record.model, self.module, record.id)
            # check if the resource already existed at the last update
            if id:
                self.id_map[record] = int(id)
                return None
            else:
                if not self._coerce_bool(record.forcecreate):
                    return None

        model = self.get_model(record.model)
        record_dict = self._create_record(model, fields)
        self.logger.debug("RECORD_DICT %s" % record_dict)
        id = self.pool.get('ir.model.data')._update(self.cr, self.uid, record.model, \
                self.module, record_dict, record.id, noupdate=self.isnoupdate(record), mode=self.mode)
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
        if is_ref(expression):
            if expression.model:
                other_model_name = expression.model
            else:
                other_model_name = column._obj
            other_model = self.get_model(other_model_name)
            if expression.search:
                q = eval(expression.search, self.eval_context)
                ids = other_model.search(self.cr, self.uid, q)
                if expression.use:
                    instances = other_model.browse(self.cr, self.uid, ids)
                    elements = [inst[expression.use] for inst in instances]
                else:
                    elements = ids
                if column._type in ("many2many", "one2many"):
                    value = [(6, 0, elements)]
                else: # many2one
                    value = elements[0]
        elif column._type == "many2one":
            value = self.get_id(expression)
        elif column._type == "one2many":
            other_model = self.get_model(column._obj)
            value = [(0, 0, self._create_record(other_model, fields)) for fields in expression]
        elif column._type == "many2many":
            ids = [self.get_id(xml_id) for xml_id in expression]
            value = [(6, 0, ids)]
        else: # scalar field
            if is_eval(expression):
                value = eval(expression.expression, self.eval_context)
            else:
                value = expression
            # raise YamlImportException('Unsupported column "%s" or value %s:%s' % (field_name, type(expression), expression))
        return value
    
    def process_context(self, node):
        self.context = node.__dict__
        if node.uid:
            self.uid = self.get_id(node.uid)
        if node.noupdate:
            self.noupdate = node.noupdate
    
    def process_python(self, node):
        def log(msg, *args):
            self.logger.log(logging.TEST, msg, *args)
        python, statements = node.items()[0]
        model = self.get_model(python.model)
        statements = statements.replace("\r\n", "\n")
        code_context = {'self': model, 'cr': self.cr, 'uid': self.uid, 'log': log, 'context': self.context}
        try:
            code = compile(statements, self.filename, 'exec')
            eval(code, {'ref': self.get_id}, code_context)
        except AssertionError, e:
            self._log_assert_failure(python.severity, 'AssertionError in Python code %s: %s', python.name, e)
            return
        except Exception, e:
            raise YamlImportAbortion(e)
        else:
            self.assert_report.record(True, python.severity)
    
    def process_workflow(self, node):
        workflow, values = node.items()[0]
        if self.isnoupdate(workflow) and self.mode != 'init':
            return
        model = self.get_model(workflow.model)
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
        wf_service = netsvc.LocalService("workflow")
        wf_service.trg_validate(uid, model, id, workflow.action, self.cr)
        
    def process_function(self, node):
        function, values = node.items()[0]
        if self.isnoupdate(function) and self.mode != 'init':
            return
        context = self.get_context(function, self.eval_context)
        args = []
        if function.eval:
            args = eval(function.eval, self.eval_context)
        for value in values:
            if not 'model' in value and (not 'eval' in value or not 'search' in value):
                raise YamlImportException('You must provide a "model" and an "eval" or "search" to evaluate.')
            value_model = self.get_model(value['model'])
            local_context = {'obj': lambda x: value_model.browse(self.cr, self.uid, x, context=context)}
            local_context.update(self.id_map)
            id = eval(value['eval'], self.eval_context, local_context)
            if id != None:
                args.append(id)
        model = self.get_model(function.model)
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
        
        pid = self.pool.get('ir.model.data')._update(self.cr, self.uid, \
                'ir.ui.menu', self.module, values, node.id, mode=self.mode, \
                noupdate=self.isnoupdate(node), res_id=res and res[0] or False)

        if node.id and parent_id:
            self.id_map[node.id] = int(parent_id)

        if node.action and pid:
            action_type = node.type or 'act_window'
            action_id = self.get_id(node.action)
            action = "ir.actions.%s,%d" % (action_type, action_id)
            self.pool.get('ir.model.data').ir_set(self.cr, self.uid, 'action', \
                    'tree_but_open', 'Menuitem', [('ir.ui.menu', int(parent_id))], action, True, True, xml_id=node.id)

    def process_act_window(self, node):
        self.validate_xml_id(node.id)
        view_id = False
        if node.view:
            view_id = self.get_id(node.view)
        context = eval(node.context, self.eval_context)

        values = {
            'name': node.name,
            'type': type or 'ir.actions.act_window',
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
        }

        self._set_group_values(node, values)

        if node.target:
            values['target'] = node.target
        id = self.pool.get('ir.model.data')._update(self.cr, self.uid, \
                'ir.actions.act_window', self.module, values, node.id, mode=self.mode)
        self.id_map[node.id] = int(id)

        if node.src_model:
            keyword = 'client_action_relate'
            value = 'ir.actions.act_window,%s' % id
            replace = node.replace or True
            self.pool.get('ir.model.data').ir_set(self.cr, self.uid, 'action', keyword, \
                    node.id, [node.src_model], value, replace=replace, noupdate=self.isnoupdate(node), isobject=True, xml_id=node.id)
        # TODO add remove ir.model.data

    def process_delete(self, node):
        ids = []
        if len(node.search):
            ids = self.pool.get(node.model).search(self.cr, self.uid, eval(node.search, self.eval_context))
        if len(node.id):
            try:
                ids.append(self.get_id(node.id))
            except:
                pass
        if len(ids):
            self.pool.get(node.model).unlink(self.cr, self.uid, ids)
            self.pool.get('ir.model.data')._unlink(self.cr, self.uid, node.model, ids, direct=True)
    
    def process_url(self, node):
        self.validate_xml_id(node.id)

        res = {'name': node.name, 'url': node.url, 'target': node.target}

        id = self.pool.get('ir.model.data')._update(self.cr, self.uid, \
                "ir.actions.url", self.module, res, node.id, mode=self.mode)
        self.id_map[node.id] = int(id)
        # ir_set
        if (not node.menu or eval(node.menu)) and id:
            keyword = node.keyword or 'client_action_multi'
            value = 'ir.actions.url,%s' % id
            replace = node.replace or True
            self.pool.get('ir.model.data').ir_set(self.cr, self.uid, 'action', \
                    keyword, node.url, ["ir.actions.url"], value, replace=replace, \
                    noupdate=self.isnoupdate(node), isobject=True, xml_id=node.id)
    
    def process_ir_set(self, node):
        if not self.mode == 'init':
            return False
        _, fields = node.items()[0]
        res = {}
        for fieldname, expression in fields.items():
            if isinstance(expression, Eval):
                value = eval(expression.expression, self.eval_context)
            else:
                value = expression
            res[fieldname] = value
        self.pool.get('ir.model.data').ir_set(self.cr, self.uid, res['key'], res['key2'], \
                res['name'], res['models'], res['value'], replace=res.get('replace',True), \
                isobject=res.get('isobject', False), meta=res.get('meta',None))

    def process_report(self, node):
        values = {}
        for dest, f in (('name','string'), ('model','model'), ('report_name','name')):
            values[dest] = getattr(node, f)
            assert values[dest], "Attribute %s of report is empty !" % (f,)
        for field,dest in (('rml','report_rml'),('xml','report_xml'),('xsl','report_xsl'),('attachment','attachment'),('attachment_use','attachment_use')):
            if getattr(node, field):
                values[dest] = getattr(node, field)
        if node.auto:
            values['auto'] = eval(node.auto)
        if node.sxw:
            sxw_content = misc.file_open(node.sxw).read()
            values['report_sxw_content'] = sxw_content
        if node.header:
            values['header'] = eval(node.header)
        values['multi'] = node.multi and eval(node.multi)
        xml_id = node.id
        self.validate_xml_id(xml_id)

        self._set_group_values(node, values)

        id = self.pool.get('ir.model.data')._update(self.cr, self.uid, "ir.actions.report.xml", \
                self.module, values, xml_id, noupdate=self.isnoupdate(node), mode=self.mode)
        self.id_map[xml_id] = int(id)

        if not node.menu or eval(node.menu):
            keyword = node.keyword or 'client_print_multi'
            value = 'ir.actions.report.xml,%s' % id
            replace = node.replace or True
            self.pool.get('ir.model.data').ir_set(self.cr, self.uid, 'action', \
                    keyword, values['name'], [values['model']], value, replace=replace, isobject=True, xml_id=xml_id)
            
    def process_none(self):
        """
        Empty node or commented node should not pass silently.
        """
        self._log_assert_failure(logging.WARNING, "You have an empty block in your tests.")
        

    def process(self, yaml_string):
        """
        Processes a Yaml string. Custom tags are interpreted by 'process_' instance methods.
        """
        is_preceded_by_comment = False
        for node in yaml.load(yaml_string):
            is_preceded_by_comment = self._log(node, is_preceded_by_comment)
            try:
                self._process_node(node)
            except YamlImportException, e:
                self.logger.log(logging.ERROR, e)
            except Exception, e:
                self.logger.log(logging.ERROR, e)
                raise e
    
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
    
    def _log(self, node, is_preceded_by_comment):
        if is_comment(node):
            is_preceded_by_comment = True
            self.logger.log(logging.TEST, node)
        elif not is_preceded_by_comment:
            if isinstance(node, types.DictionaryType):
                msg = "Creating %s\n with %s"
                args = node.items()[0]
                self.logger.log(logging.TEST, msg, *args)
            else:
                self.logger.log(logging.TEST, node)
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
