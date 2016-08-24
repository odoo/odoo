# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import cStringIO
import csv
import logging
import os.path
import re
import sys
import time

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

import pytz
from lxml import etree, builder

import openerp
import openerp.release
import openerp.workflow

import assertion_report
import misc

from config import config
# List of etree._Element subclasses that we choose to ignore when parsing XML.
from misc import SKIPPED_ELEMENT_TYPES
from misc import pickle, unquote
from openerp import SUPERUSER_ID
from translate import _
from yaml_import import convert_yaml_import

_logger = logging.getLogger(__name__)

# Import of XML records requires the unsafe eval as well,
# almost everywhere, which is ok because it supposedly comes
# from trusted data, but at least we make it obvious now.
unsafe_eval = eval
from safe_eval import safe_eval as eval

class ParseError(Exception):
    def __init__(self, msg, text, filename, lineno):
        self.msg = msg
        self.text = text
        self.filename = filename
        self.lineno = lineno

    def __str__(self):
        return '"%s" while parsing %s:%s, near\n%s' \
            % (self.msg, self.filename, self.lineno, self.text)

def _ref(self, cr):
    return lambda x: self.id_get(cr, x)

def _obj(pool, cr, uid, model_str, context=None):
    model = pool[model_str]
    return lambda x: model.browse(cr, uid, x, context=context)

def _get_idref(self, cr, uid, model_str, context, idref):
    idref2 = dict(idref,
                  time=time,
                  DateTime=datetime,
                  datetime=datetime,
                  timedelta=timedelta,
                  relativedelta=relativedelta,
                  version=openerp.release.major_version,
                  ref=_ref(self, cr),
                  pytz=pytz)
    if len(model_str):
        idref2['obj'] = _obj(self.pool, cr, uid, model_str, context=context)
    return idref2

def _fix_multiple_roots(node):
    """
    Surround the children of the ``node`` element of an XML field with a
    single root "data" element, to prevent having a document with multiple
    roots once parsed separately.

    XML nodes should have one root only, but we'd like to support
    direct multiple roots in our partial documents (like inherited view architectures).
    As a convention we'll surround multiple root with a container "data" element, to be
    ignored later when parsing.
    """
    real_nodes = [x for x in node if not isinstance(x, SKIPPED_ELEMENT_TYPES)]
    if len(real_nodes) > 1:
        data_node = etree.Element("data")
        for child in node:
            data_node.append(child)
        node.append(data_node)

def _eval_xml(self, node, pool, cr, uid, idref, context=None):
    if context is None:
        context = {}
    if node.tag in ('field','value'):
        t = node.get('type','char')
        f_model = node.get('model', '').encode('utf-8')
        if node.get('search'):
            f_search = node.get("search",'').encode('utf-8')
            f_use = node.get("use",'id').encode('utf-8')
            f_name = node.get("name",'').encode('utf-8')
            idref2 = {}
            if f_search:
                idref2 = _get_idref(self, cr, uid, f_model, context, idref)
            q = unsafe_eval(f_search, idref2)
            ids = pool[f_model].search(cr, uid, q)
            if f_use != 'id':
                ids = map(lambda x: x[f_use], pool[f_model].read(cr, uid, ids, [f_use]))
            _cols = pool[f_model]._columns
            if (f_name in _cols) and _cols[f_name]._type=='many2many':
                return ids
            f_val = False
            if len(ids):
                f_val = ids[0]
                if isinstance(f_val, tuple):
                    f_val = f_val[0]
            return f_val
        a_eval = node.get('eval','')
        if a_eval:
            idref2 = _get_idref(self, cr, uid, f_model, context, idref)
            try:
                return unsafe_eval(a_eval, idref2)
            except Exception:
                logging.getLogger('openerp.tools.convert.init').error(
                    'Could not eval(%s) for %s in %s', a_eval, node.get('name'), context)
                raise
        def _process(s, idref):
            matches = re.finditer('[^%]%\((.*?)\)[ds]', s)
            done = []
            for m in matches:
                found = m.group()[1:]
                if found in done:
                    continue
                done.append(found)
                id = m.groups()[0]
                if not id in idref:
                    idref[id] = self.id_get(cr, id)
                s = s.replace(found, str(idref[id]))

            s = s.replace('%%', '%') # Quite wierd but it's for (somewhat) backward compatibility sake

            return s

        if t == 'xml':
            _fix_multiple_roots(node)
            return '<?xml version="1.0"?>\n'\
                +_process("".join([etree.tostring(n, encoding='utf-8')
                                   for n in node]), idref)
        if t == 'html':
            return _process("".join([etree.tostring(n, encoding='utf-8')
                                   for n in node]), idref)

        data = node.text
        if node.get('file'):
            with openerp.tools.file_open(node.get('file'), 'rb') as f:
                data = f.read()

        if t == 'file':
            from ..modules import module
            path = data.strip()
            if not module.get_module_resource(self.module, path):
                raise IOError("No such file or directory: '%s' in %s" % (
                    path, self.module))
            return '%s,%s' % (self.module, path)

        if t == 'char':
            return data

        if t == 'base64':
            return data.encode('base64')

        if t == 'int':
            d = data.strip()
            if d == 'None':
                return None
            return int(d)

        if t == 'float':
            return float(data.strip())

        if t in ('list','tuple'):
            res=[]
            for n in node.iterchildren(tag='value'):
                res.append(_eval_xml(self,n,pool,cr,uid,idref))
            if t=='tuple':
                return tuple(res)
            return res
    elif node.tag == "function":
        args = []
        a_eval = node.get('eval','')
        # FIXME: should probably be exclusive
        if a_eval:
            idref['ref'] = lambda x: self.id_get(cr, x)
            args = unsafe_eval(a_eval, idref)
        for n in node:
            return_val = _eval_xml(self,n, pool, cr, uid, idref, context)
            if return_val is not None:
                args.append(return_val)
        model = pool[node.get('model', '')]
        method = node.get('name')
        res = getattr(model, method)(cr, uid, *args)
        return res
    elif node.tag == "test":
        return node.text

class xml_import(object):

    @staticmethod
    def nodeattr2bool(node, attr, default=False):
        if not node.get(attr):
            return default
        val = node.get(attr).strip()
        if not val:
            return default
        return val.lower() not in ('0', 'false', 'off')

    def isnoupdate(self, data_node=None):
        return self.noupdate or (len(data_node) and self.nodeattr2bool(data_node, 'noupdate', False))

    def get_context(self, data_node, node, eval_dict):
        data_node_context = (len(data_node) and data_node.get('context','').encode('utf8'))
        node_context = node.get("context",'').encode('utf8')
        context = {}
        for ctx in (data_node_context, node_context):
            if ctx:
                try:
                    ctx_res = unsafe_eval(ctx, eval_dict)
                    if isinstance(context, dict):
                        context.update(ctx_res)
                    else:
                        context = ctx_res
                except NameError:
                    # Some contexts contain references that are only valid at runtime at
                    # client-side, so in that case we keep the original context string
                    # as it is. We also log it, just in case.
                    context = ctx
                    _logger.debug('Context value (%s) for element with id "%s" or its data node does not parse '\
                                                    'at server-side, keeping original string, in case it\'s meant for client side only',
                                                    ctx, node.get('id','n/a'), exc_info=True)
        return context

    def get_uid(self, cr, uid, data_node, node):
        node_uid = node.get('uid','') or (len(data_node) and data_node.get('uid',''))
        if node_uid:
            return self.id_get(cr, node_uid)
        return uid

    def _test_xml_id(self, xml_id):
        id = xml_id
        if '.' in xml_id:
            module, id = xml_id.split('.', 1)
            assert '.' not in id, """The ID reference "%s" must contain
maximum one dot. They are used to refer to other modules ID, in the
form: module.record_id""" % (xml_id,)
            if module != self.module:
                modcnt = self.pool['ir.module.module'].search_count(self.cr, self.uid, ['&', ('name', '=', module), ('state', 'in', ['installed'])])
                assert modcnt == 1, """The ID "%s" refers to an uninstalled module""" % (xml_id,)

        if len(id) > 64:
            _logger.error('id: %s is to long (max: 64)', id)

    def _tag_delete(self, cr, rec, data_node=None, mode=None):
        d_model = rec.get("model")
        d_search = rec.get("search",'').encode('utf-8')
        d_id = rec.get("id")
        ids = []

        if d_search:
            idref = _get_idref(self, cr, self.uid, d_model, context={}, idref={})
            try:
                ids = self.pool[d_model].search(cr, self.uid, unsafe_eval(d_search, idref))
            except ValueError:
                _logger.warning('Skipping deletion for failed search `%r`', d_search, exc_info=True)
                pass
        if d_id:
            try:
                ids.append(self.id_get(cr, d_id))
            except ValueError:
                # d_id cannot be found. doesn't matter in this case
                _logger.warning('Skipping deletion for missing XML ID `%r`', d_id, exc_info=True)
                pass
        if ids:
            self.pool[d_model].unlink(cr, self.uid, ids)

    def _remove_ir_values(self, cr, name, value, model):
        ir_values_obj = self.pool['ir.values']
        ir_value_ids = ir_values_obj.search(cr, self.uid, [('name','=',name),('value','=',value),('model','=',model)])
        if ir_value_ids:
            ir_values_obj.unlink(cr, self.uid, ir_value_ids)

        return True

    def _tag_report(self, cr, rec, data_node=None, mode=None):
        res = {}
        for dest,f in (('name','string'),('model','model'),('report_name','name')):
            res[dest] = rec.get(f,'').encode('utf8')
            assert res[dest], "Attribute %s of report is empty !" % (f,)
        for field,dest in (('rml','report_rml'),('file','report_rml'),('xml','report_xml'),('xsl','report_xsl'),
                           ('attachment','attachment'),('attachment_use','attachment_use'), ('usage','usage'),
                           ('report_type', 'report_type'), ('parser', 'parser')):
            if rec.get(field):
                res[dest] = rec.get(field).encode('utf8')
        if rec.get('auto'):
            res['auto'] = eval(rec.get('auto','False'))
        if rec.get('sxw'):
            sxw_content = misc.file_open(rec.get('sxw')).read()
            res['report_sxw_content'] = sxw_content
        if rec.get('header'):
            res['header'] = eval(rec.get('header','False'))

        res['multi'] = rec.get('multi') and eval(rec.get('multi','False'))

        xml_id = rec.get('id','').encode('utf8')
        self._test_xml_id(xml_id)

        if rec.get('groups'):
            g_names = rec.get('groups','').split(',')
            groups_value = []
            for group in g_names:
                if group.startswith('-'):
                    group_id = self.id_get(cr, group[1:])
                    groups_value.append((3, group_id))
                else:
                    group_id = self.id_get(cr, group)
                    groups_value.append((4, group_id))
            res['groups_id'] = groups_value
        if rec.get('paperformat'):
            pf_name = rec.get('paperformat')
            pf_id = self.id_get(cr,pf_name)
            res['paperformat_id'] = pf_id

        id = self.pool['ir.model.data']._update(cr, self.uid, "ir.actions.report.xml", self.module, res, xml_id, noupdate=self.isnoupdate(data_node), mode=self.mode)
        self.idref[xml_id] = int(id)

        if not rec.get('menu') or eval(rec.get('menu','False')):
            keyword = str(rec.get('keyword', 'client_print_multi'))
            value = 'ir.actions.report.xml,'+str(id)
            ir_values_id = self.pool['ir.values'].set_action(cr, self.uid, res['name'], keyword, res['model'], value)
            self.pool['ir.actions.report.xml'].write(cr, self.uid, id, {'ir_values_id': ir_values_id})
        elif self.mode=='update' and eval(rec.get('menu','False'))==False:
            # Special check for report having attribute menu=False on update
            value = 'ir.actions.report.xml,'+str(id)
            self._remove_ir_values(cr, res['name'], value, res['model'])
            self.pool['ir.actions.report.xml'].write(cr, self.uid, id, {'ir_values_id': False})
        return id

    def _tag_function(self, cr, rec, data_node=None, mode=None):
        if self.isnoupdate(data_node) and self.mode != 'init':
            return
        context = self.get_context(data_node, rec, {'ref': _ref(self, cr)})
        uid = self.get_uid(cr, self.uid, data_node, rec)
        _eval_xml(self,rec, self.pool, cr, uid, self.idref, context=context)
        return

    def _tag_act_window(self, cr, rec, data_node=None, mode=None):
        name = rec.get('name','').encode('utf-8')
        xml_id = rec.get('id','').encode('utf8')
        self._test_xml_id(xml_id)
        type = rec.get('type','').encode('utf-8') or 'ir.actions.act_window'
        view_id = False
        if rec.get('view_id'):
            view_id = self.id_get(cr, rec.get('view_id','').encode('utf-8'))
        domain = rec.get('domain','').encode('utf-8') or '[]'
        res_model = rec.get('res_model','').encode('utf-8')
        src_model = rec.get('src_model','').encode('utf-8')
        view_type = rec.get('view_type','').encode('utf-8') or 'form'
        view_mode = rec.get('view_mode','').encode('utf-8') or 'tree,form'
        usage = rec.get('usage','').encode('utf-8')
        limit = rec.get('limit','').encode('utf-8')
        auto_refresh = rec.get('auto_refresh','').encode('utf-8')
        uid = self.uid

        # Act_window's 'domain' and 'context' contain mostly literals
        # but they can also refer to the variables provided below
        # in eval_context, so we need to eval() them before storing.
        # Among the context variables, 'active_id' refers to
        # the currently selected items in a list view, and only
        # takes meaning at runtime on the client side. For this
        # reason it must remain a bare variable in domain and context,
        # even after eval() at server-side. We use the special 'unquote'
        # class to achieve this effect: a string which has itself, unquoted,
        # as representation.
        active_id = unquote("active_id")
        active_ids = unquote("active_ids")
        active_model = unquote("active_model")

        def ref(str_id):
            return self.id_get(cr, str_id)

        # Include all locals() in eval_context, for backwards compatibility
        eval_context = {
            'name': name,
            'xml_id': xml_id,
            'type': type,
            'view_id': view_id,
            'domain': domain,
            'res_model': res_model,
            'src_model': src_model,
            'view_type': view_type,
            'view_mode': view_mode,
            'usage': usage,
            'limit': limit,
            'auto_refresh': auto_refresh,
            'uid' : uid,
            'active_id': active_id,
            'active_ids': active_ids,
            'active_model': active_model,
            'ref' : ref,
        }
        context = self.get_context(data_node, rec, eval_context)

        try:
            domain = unsafe_eval(domain, eval_context)
        except NameError:
            # Some domains contain references that are only valid at runtime at
            # client-side, so in that case we keep the original domain string
            # as it is. We also log it, just in case.
            _logger.debug('Domain value (%s) for element with id "%s" does not parse '\
                'at server-side, keeping original string, in case it\'s meant for client side only',
                domain, xml_id or 'n/a', exc_info=True)
        res = {
            'name': name,
            'type': type,
            'view_id': view_id,
            'domain': domain,
            'context': context,
            'res_model': res_model,
            'src_model': src_model,
            'view_type': view_type,
            'view_mode': view_mode,
            'usage': usage,
            'limit': limit,
            'auto_refresh': auto_refresh,
        }

        if rec.get('groups'):
            g_names = rec.get('groups','').split(',')
            groups_value = []
            for group in g_names:
                if group.startswith('-'):
                    group_id = self.id_get(cr, group[1:])
                    groups_value.append((3, group_id))
                else:
                    group_id = self.id_get(cr, group)
                    groups_value.append((4, group_id))
            res['groups_id'] = groups_value

        if rec.get('target'):
            res['target'] = rec.get('target','')
        if rec.get('multi'):
            res['multi'] = eval(rec.get('multi', 'False'))
        id = self.pool['ir.model.data']._update(cr, self.uid, 'ir.actions.act_window', self.module, res, xml_id, noupdate=self.isnoupdate(data_node), mode=self.mode)
        self.idref[xml_id] = int(id)

        if src_model:
            #keyword = 'client_action_relate'
            keyword = rec.get('key2','').encode('utf-8') or 'client_action_relate'
            value = 'ir.actions.act_window,'+str(id)
            replace = rec.get('replace','') or True
            self.pool['ir.model.data'].ir_set(cr, self.uid, 'action', keyword, xml_id, [src_model], value, replace=replace, isobject=True, xml_id=xml_id)
        # TODO add remove ir.model.data

    def _tag_ir_set(self, cr, rec, data_node=None, mode=None):
        """
            .. deprecated:: 9.0

            Use the <record> notation with ``ir.values`` as model instead.
        """
        if self.mode != 'init':
            return
        res = {}
        for field in rec.findall('./field'):
            f_name = field.get("name",'').encode('utf-8')
            f_val = _eval_xml(self,field,self.pool, cr, self.uid, self.idref)
            res[f_name] = f_val
        self.pool['ir.model.data'].ir_set(cr, self.uid, res['key'], res['key2'], res['name'], res['models'], res['value'], replace=res.get('replace',True), isobject=res.get('isobject', False), meta=res.get('meta',None))

    def _tag_workflow(self, cr, rec, data_node=None, mode=None):
        if self.isnoupdate(data_node) and self.mode != 'init':
            return
        model = rec.get('model').encode('ascii')
        w_ref = rec.get('ref')
        if w_ref:
            id = self.id_get(cr, w_ref)
        else:
            number_children = len(rec)
            assert number_children > 0,\
                'You must define a child node if you dont give a ref'
            assert number_children == 1,\
                'Only one child node is accepted (%d given)' % number_children
            id = _eval_xml(self, rec[0], self.pool, cr, self.uid, self.idref)

        uid = self.get_uid(cr, self.uid, data_node, rec)
        openerp.workflow.trg_validate(
            uid, model, id, rec.get('action').encode('ascii'), cr)

    def _tag_menuitem(self, cr, rec, data_node=None, mode=None):
        rec_id = rec.get("id",'').encode('ascii')
        self._test_xml_id(rec_id)

        # The parent attribute was specified, if non-empty determine its ID, otherwise
        # explicitly make a top-level menu
        if rec.get('parent'):
            menu_parent_id = self.id_get(cr, rec.get('parent',''))
        else:
            # we get here with <menuitem parent="">, explicit clear of parent, or
            # if no parent attribute at all but menu name is not a menu path
            menu_parent_id = False
        values = {'parent_id': menu_parent_id}
        if rec.get('name'):
            values['name'] = rec.get('name')
        try:
            res = [ self.id_get(cr, rec.get('id','')) ]
        except:
            res = None

        if rec.get('action'):
            a_action = rec.get('action','').encode('utf8')

            # determine the type of action
            action_type, action_id = self.model_id_get(cr, a_action)
            action_type = action_type.split('.')[-1] # keep only type part
            values['action'] = "ir.actions.%s,%d" % (action_type, action_id)

            if not values.get('name') and action_type in ('act_window', 'wizard', 'url', 'client', 'server'):
                a_table = 'ir_act_%s' % action_type.replace('act_', '')
                cr.execute('select name from "%s" where id=%%s' % a_table, (int(action_id),))
                resw = cr.fetchone()
                if resw:
                    values['name'] = resw[0]

        if not values.get('name'):
            # ensure menu has a name
            values['name'] = rec_id or '?'

        if rec.get('sequence'):
            values['sequence'] = int(rec.get('sequence'))

        if rec.get('groups'):
            g_names = rec.get('groups','').split(',')
            groups_value = []
            for group in g_names:
                if group.startswith('-'):
                    group_id = self.id_get(cr, group[1:])
                    groups_value.append((3, group_id))
                else:
                    group_id = self.id_get(cr, group)
                    groups_value.append((4, group_id))
            values['groups_id'] = groups_value

        if not values.get('parent_id'):
            if rec.get('web_icon'):
                values['web_icon'] = rec.get('web_icon')

        pid = self.pool['ir.model.data']._update(cr, self.uid, 'ir.ui.menu', self.module, values, rec_id, noupdate=self.isnoupdate(data_node), mode=self.mode, res_id=res and res[0] or False)

        if rec_id and pid:
            self.idref[rec_id] = int(pid)

        return 'ir.ui.menu', pid

    def _assert_equals(self, f1, f2, prec=4):
        return not round(f1 - f2, prec)

    def _tag_assert(self, cr, rec, data_node=None, mode=None):
        if self.isnoupdate(data_node) and self.mode != 'init':
            return

        rec_model = rec.get("model",'').encode('ascii')
        model = self.pool[rec_model]
        rec_id = rec.get("id",'').encode('ascii')
        self._test_xml_id(rec_id)
        rec_src = rec.get("search",'').encode('utf8')
        rec_src_count = rec.get("count")

        rec_string = rec.get("string",'').encode('utf8') or 'unknown'

        ids = None
        eval_dict = {'ref': _ref(self, cr)}
        context = self.get_context(data_node, rec, eval_dict)
        uid = self.get_uid(cr, self.uid, data_node, rec)
        if rec_id:
            ids = [self.id_get(cr, rec_id)]
        elif rec_src:
            q = unsafe_eval(rec_src, eval_dict)
            ids = self.pool[rec_model].search(cr, uid, q, context=context)
            if rec_src_count:
                count = int(rec_src_count)
                if len(ids) != count:
                    self.assertion_report.record_failure()
                    msg = 'assertion "%s" failed!\n'    \
                          ' Incorrect search count:\n'  \
                          ' expected count: %d\n'       \
                          ' obtained count: %d\n'       \
                          % (rec_string, count, len(ids))
                    _logger.error(msg)
                    return

        assert ids is not None,\
            'You must give either an id or a search criteria'
        ref = _ref(self, cr)
        for id in ids:
            brrec =  model.browse(cr, uid, id, context)
            class d(dict):
                def __getitem__(self2, key):
                    if key in brrec:
                        return brrec[key]
                    return dict.__getitem__(self2, key)
            globals_dict = d()
            globals_dict['floatEqual'] = self._assert_equals
            globals_dict['ref'] = ref
            globals_dict['_ref'] = ref
            for test in rec.findall('./test'):
                f_expr = test.get("expr",'').encode('utf-8')
                expected_value = _eval_xml(self, test, self.pool, cr, uid, self.idref, context=context) or True
                expression_value = unsafe_eval(f_expr, globals_dict)
                if expression_value != expected_value: # assertion failed
                    self.assertion_report.record_failure()
                    msg = 'assertion "%s" failed!\n'    \
                          ' xmltag: %s\n'               \
                          ' expected value: %r\n'       \
                          ' obtained value: %r\n'       \
                          % (rec_string, etree.tostring(test), expected_value, expression_value)
                    _logger.error(msg)
                    return
        else: # all tests were successful for this assertion tag (no break)
            self.assertion_report.record_success()

    def _tag_record(self, cr, rec, data_node=None, mode=None):
        rec_model = rec.get("model").encode('ascii')
        model = self.pool[rec_model]
        rec_id = rec.get("id",'').encode('ascii')
        rec_context = rec.get("context", {})
        if rec_context:
            rec_context = unsafe_eval(rec_context)

        if self.xml_filename and rec_id:
            rec_context['install_mode_data'] = dict(
                xml_file=self.xml_filename,
                xml_id=rec_id,
                model=rec_model,
            )

        self._test_xml_id(rec_id)
        # in update mode, the record won't be updated if the data node explicitely
        # opt-out using @noupdate="1". A second check will be performed in
        # ir.model.data#_update() using the record's ir.model.data `noupdate` field.
        if self.isnoupdate(data_node) and self.mode != 'init':
            # check if the xml record has no id, skip
            if not rec_id:
                return None

            if '.' in rec_id:
                module,rec_id2 = rec_id.split('.')
            else:
                module = self.module
                rec_id2 = rec_id
            id = self.pool['ir.model.data']._update_dummy(cr, self.uid, rec_model, module, rec_id2)
            if id:
                # if the resource already exists, don't update it but store
                # its database id (can be useful)
                self.idref[rec_id] = int(id)
                return None
            elif not self.nodeattr2bool(rec, 'forcecreate', True):
                # if it doesn't exist and we shouldn't create it, skip it
                return None
            # else create it normally

        res = {}
        for field in rec.findall('./field'):
            #TODO: most of this code is duplicated above (in _eval_xml)...
            f_name = field.get("name").encode('utf-8')
            f_ref = field.get("ref",'').encode('utf-8')
            f_search = field.get("search",'').encode('utf-8')
            f_model = field.get("model",'').encode('utf-8')
            if not f_model and f_name in model._fields:
                f_model = model._fields[f_name].comodel_name
            f_use = field.get("use",'').encode('utf-8') or 'id'
            f_val = False

            if f_search:
                q = unsafe_eval(f_search, self.idref)
                assert f_model, 'Define an attribute model="..." in your .XML file !'
                f_obj = self.pool[f_model]
                # browse the objects searched
                s = f_obj.browse(cr, self.uid, f_obj.search(cr, self.uid, q))
                # column definitions of the "local" object
                _fields = self.pool[rec_model]._fields
                # if the current field is many2many
                if (f_name in _fields) and _fields[f_name].type == 'many2many':
                    f_val = [(6, 0, map(lambda x: x[f_use], s))]
                elif len(s):
                    # otherwise (we are probably in a many2one field),
                    # take the first element of the search
                    f_val = s[0][f_use]
            elif f_ref:
                if f_name in model._fields and model._fields[f_name].type == 'reference':
                    val = self.model_id_get(cr, f_ref)
                    f_val = val[0] + ',' + str(val[1])
                else:
                    f_val = self.id_get(cr, f_ref)
            else:
                f_val = _eval_xml(self,field, self.pool, cr, self.uid, self.idref)
                if f_name in model._fields:
                    if model._fields[f_name].type == 'integer':
                        f_val = int(f_val)
            res[f_name] = f_val

        id = self.pool['ir.model.data']._update(cr, self.uid, rec_model, self.module, res, rec_id or False, not self.isnoupdate(data_node), noupdate=self.isnoupdate(data_node), mode=self.mode, context=rec_context )
        if rec_id:
            self.idref[rec_id] = int(id)
        if config.get('import_partial'):
            cr.commit()
        return rec_model, id

    def _tag_template(self, cr, el, data_node=None, mode=None):
        # This helper transforms a <template> element into a <record> and forwards it
        tpl_id = el.get('id', el.get('t-name', '')).encode('ascii')
        full_tpl_id = tpl_id
        if '.' not in full_tpl_id:
            full_tpl_id = '%s.%s' % (self.module, tpl_id)
        # set the full template name for qweb <module>.<id>
        if not el.get('inherit_id'):
            el.set('t-name', full_tpl_id)
            el.tag = 't'
        else:
            el.tag = 'data'
        el.attrib.pop('id', None)

        record_attrs = {
            'id': tpl_id,
            'model': 'ir.ui.view',
        }
        for att in ['forcecreate', 'context']:
            if att in el.keys():
                record_attrs[att] = el.attrib.pop(att)

        Field = builder.E.field
        name = el.get('name', tpl_id)

        record = etree.Element('record', attrib=record_attrs)
        record.append(Field(name, name='name'))
        record.append(Field(full_tpl_id, name='key'))
        record.append(Field("qweb", name='type'))
        record.append(Field(el.get('priority', "16"), name='priority'))
        if 'inherit_id' in el.attrib:
            record.append(Field(name='inherit_id', ref=el.get('inherit_id')))
        if 'website_id' in el.attrib:
            record.append(Field(name='website_id', ref=el.get('website_id')))
        if 'key' in el.attrib:
            record.append(Field(el.get('key'), name='key'))
        if el.get('active') in ("True", "False"):
            view_id = self.id_get(cr, tpl_id, raise_if_not_found=False)
            if mode != "update" or not view_id:
                record.append(Field(name='active', eval=el.get('active')))
        if el.get('customize_show') in ("True", "False"):
            record.append(Field(name='customize_show', eval=el.get('customize_show')))
        groups = el.attrib.pop('groups', None)
        if groups:
            grp_lst = map(lambda x: "ref('%s')" % x, groups.split(','))
            record.append(Field(name="groups_id", eval="[(6, 0, ["+', '.join(grp_lst)+"])]"))
        if el.attrib.pop('page', None) == 'True':
            record.append(Field(name="page", eval="True"))
        if el.get('primary') == 'True':
            # Pseudo clone mode, we'll set the t-name to the full canonical xmlid
            el.append(
                builder.E.xpath(
                    builder.E.attribute(full_tpl_id, name='t-name'),
                    expr=".",
                    position="attributes",
                )
            )
            record.append(Field('primary', name='mode'))
        # inject complete <template> element (after changing node name) into
        # the ``arch`` field
        record.append(Field(el, name="arch", type="xml"))

        return self._tag_record(cr, record, data_node)

    def id_get(self, cr, id_str, raise_if_not_found=True):
        if id_str in self.idref:
            return self.idref[id_str]
        res = self.model_id_get(cr, id_str, raise_if_not_found)
        if res and len(res)>1: res = res[1]
        return res

    def model_id_get(self, cr, id_str, raise_if_not_found=True):
        model_data_obj = self.pool['ir.model.data']
        mod = self.module
        if '.' not in id_str:
            id_str = '%s.%s' % (mod, id_str)
        return model_data_obj.xmlid_to_res_model_res_id(
            cr, self.uid, id_str,
            raise_if_not_found=raise_if_not_found)

    def parse(self, de, mode=None):
        roots = ['openerp','data','odoo']
        if de.tag not in roots:
            raise Exception("Root xml tag must be <openerp>, <odoo> or <data>.")
        for rec in de:
            if rec.tag in roots:
                self.parse(rec, mode)
            elif rec.tag in self._tags:
                try:
                    self._tags[rec.tag](self.cr, rec, de, mode=mode)
                except Exception, e:
                    self.cr.rollback()
                    exc_info = sys.exc_info()
                    raise ParseError, (misc.ustr(e), etree.tostring(rec).rstrip(), rec.getroottree().docinfo.URL, rec.sourceline), exc_info[2]
        return True

    def __init__(self, cr, module, idref, mode, report=None, noupdate=False, xml_filename=None):

        self.mode = mode
        self.module = module
        self.cr = cr
        self.idref = idref
        self.pool = openerp.registry(cr.dbname)
        self.uid = 1
        if report is None:
            report = assertion_report.assertion_report()
        self.assertion_report = report
        self.noupdate = noupdate
        self.xml_filename = xml_filename
        self._tags = {
            'record': self._tag_record,
            'delete': self._tag_delete,
            'function': self._tag_function,
            'menuitem': self._tag_menuitem,
            'template': self._tag_template,
            'workflow': self._tag_workflow,
            'report': self._tag_report,
            'ir_set': self._tag_ir_set, # deprecated:: 9.0
            'act_window': self._tag_act_window,
            'assert': self._tag_assert,
        }

def convert_file(cr, module, filename, idref, mode='update', noupdate=False, kind=None, report=None, pathname=None):
    if pathname is None:
        pathname = os.path.join(module, filename)
    fp = misc.file_open(pathname)
    ext = os.path.splitext(filename)[1].lower()

    try:
        if ext == '.csv':
            convert_csv_import(cr, module, pathname, fp.read(), idref, mode, noupdate)
        elif ext == '.sql':
            convert_sql_import(cr, fp)
        elif ext == '.yml':
            convert_yaml_import(cr, module, fp, kind, idref, mode, noupdate, report)
        elif ext == '.xml':
            convert_xml_import(cr, module, fp, idref, mode, noupdate, report)
        elif ext == '.js':
            pass # .js files are valid but ignored here.
        else:
            raise ValueError("Can't load unknown file type %s.", filename)
    finally:
        fp.close()

def convert_sql_import(cr, fp):
    cr.execute(fp.read())

def convert_csv_import(cr, module, fname, csvcontent, idref=None, mode='init',
        noupdate=False):
    '''Import csv file :
        quote: "
        delimiter: ,
        encoding: utf-8'''
    if not idref:
        idref={}
    model = ('.'.join(fname.split('.')[:-1]).split('-'))[0]
    #remove folder path from model
    head, model = os.path.split(model)

    input = cStringIO.StringIO(csvcontent) #FIXME
    reader = csv.reader(input, quotechar='"', delimiter=',')
    fields = reader.next()
    fname_partial = ""
    if config.get('import_partial'):
        fname_partial = module + '/'+ fname
        if not os.path.isfile(config.get('import_partial')):
            pickle.dump({}, file(config.get('import_partial'),'w+'))
        else:
            data = pickle.load(file(config.get('import_partial')))
            if fname_partial in data:
                if not data[fname_partial]:
                    return
                else:
                    for i in range(data[fname_partial]):
                        reader.next()

    if not (mode == 'init' or 'id' in fields):
        _logger.error("Import specification does not contain 'id' and we are in init mode, Cannot continue.")
        return

    uid = 1
    datas = []
    for line in reader:
        if not (line and any(line)):
            continue
        try:
            datas.append(map(misc.ustr, line))
        except:
            _logger.error("Cannot import the line: %s", line)

    registry = openerp.registry(cr.dbname)
    result, rows, warning_msg, dummy = registry[model].import_data(cr, uid, fields, datas,mode, module, noupdate, filename=fname_partial)
    if result < 0:
        # Report failed import and abort module install
        raise Exception(_('Module loading %s failed: file %s could not be processed:\n %s') % (module, fname, warning_msg))
    if config.get('import_partial'):
        data = pickle.load(file(config.get('import_partial')))
        data[fname_partial] = 0
        pickle.dump(data, file(config.get('import_partial'),'wb'))
        cr.commit()

def convert_xml_import(cr, module, xmlfile, idref=None, mode='init', noupdate=False, report=None):
    doc = etree.parse(xmlfile)
    relaxng = etree.RelaxNG(
        etree.parse(os.path.join(config['root_path'],'import_xml.rng' )))
    try:
        relaxng.assert_(doc)
    except Exception:
        _logger.info('The XML file does not fit the required schema !', exc_info=True)
        _logger.info(misc.ustr(relaxng.error_log.last_error))
        raise

    if idref is None:
        idref={}
    if isinstance(xmlfile, file):
        xml_filename = xmlfile.name
    else:
        xml_filename = xmlfile
    obj = xml_import(cr, module, idref, mode, report=report, noupdate=noupdate, xml_filename=xml_filename)
    obj.parse(doc.getroot(), mode=mode)
    return True
