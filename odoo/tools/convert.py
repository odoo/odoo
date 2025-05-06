# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

__all__ = [
    'convert_file', 'convert_sql_import',
    'convert_csv_import', 'convert_xml_import'
]

import base64
import io
import logging
import os.path
import pprint
import re
import subprocess
import warnings

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

import pytz
from lxml import etree, builder
try:
    import jingtrang
except ImportError:
    jingtrang = None

import odoo
from . import pycompat
from .config import config
from .misc import file_open, unquote, ustr, SKIPPED_ELEMENT_TYPES
from .translate import _
from odoo import SUPERUSER_ID, api
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

from .safe_eval import safe_eval as s_eval, pytz, time
safe_eval = lambda expr, ctx={}: s_eval(expr, ctx, nocopy=True)

class ParseError(Exception):
    ...

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

def _get_idref(self, env, model_str, idref):
    idref2 = dict(idref,
                  Command=odoo.fields.Command,
                  time=time,
                  DateTime=datetime,
                  datetime=datetime,
                  timedelta=timedelta,
                  relativedelta=relativedelta,
                  version=odoo.release.major_version,
                  ref=self.id_get,
                  pytz=pytz)
    if model_str:
        idref2['obj'] = env[model_str].browse
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

def _eval_xml(self, node, env):
    if node.tag in ('field','value'):
        t = node.get('type','char')
        f_model = node.get('model')
        if node.get('search'):
            f_search = node.get("search")
            f_use = node.get("use",'id')
            f_name = node.get("name")
            idref2 = {}
            if f_search:
                idref2 = _get_idref(self, env, f_model, self.idref)
            q = safe_eval(f_search, idref2)
            ids = env[f_model].search(q).ids
            if f_use != 'id':
                ids = [x[f_use] for x in env[f_model].browse(ids).read([f_use])]
            _fields = env[f_model]._fields
            if (f_name in _fields) and _fields[f_name].type == 'many2many':
                return ids
            f_val = False
            if len(ids):
                f_val = ids[0]
                if isinstance(f_val, tuple):
                    f_val = f_val[0]
            return f_val
        a_eval = node.get('eval')
        if a_eval:
            idref2 = _get_idref(self, env, f_model, self.idref)
            try:
                return safe_eval(a_eval, idref2)
            except Exception:
                logging.getLogger('odoo.tools.convert.init').error(
                    'Could not eval(%s) for %s in %s', a_eval, node.get('name'), env.context)
                raise
        def _process(s):
            matches = re.finditer(br'[^%]%\((.*?)\)[ds]'.decode('utf-8'), s)
            done = set()
            for m in matches:
                found = m.group()[1:]
                if found in done:
                    continue
                done.add(found)
                id = m.groups()[0]
                if not id in self.idref:
                    self.idref[id] = self.id_get(id)
                # So funny story: in Python 3, bytes(n: int) returns a
                # bytestring of n nuls. In Python 2 it obviously returns the
                # stringified number, which is what we're expecting here
                s = s.replace(found, str(self.idref[id]))
            s = s.replace('%%', '%') # Quite weird but it's for (somewhat) backward compatibility sake
            return s

        if t == 'xml':
            _fix_multiple_roots(node)
            return '<?xml version="1.0"?>\n'\
                +_process("".join(etree.tostring(n, encoding='unicode') for n in node))
        if t == 'html':
            return _process("".join(etree.tostring(n, method='html', encoding='unicode') for n in node))

        data = node.text
        if node.get('file'):
            with file_open(node.get('file'), 'rb', env=env) as f:
                data = f.read()

        if t == 'base64':
            return base64.b64encode(data)

        # after that, only text content makes sense
        data = pycompat.to_text(data)
        if t == 'file':
            from ..modules import module
            path = data.strip()
            if not module.get_module_resource(self.module, path):
                raise IOError("No such file or directory: '%s' in %s" % (
                    path, self.module))
            return '%s,%s' % (self.module, path)

        if t == 'char':
            return data

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
                res.append(_eval_xml(self, n, env))
            if t=='tuple':
                return tuple(res)
            return res
    elif node.tag == "function":
        model_str = node.get('model')
        model = env[model_str]
        method_name = node.get('name')
        # determine arguments
        args = []
        kwargs = {}
        a_eval = node.get('eval')

        if a_eval:
            idref2 = _get_idref(self, env, model_str, self.idref)
            args = list(safe_eval(a_eval, idref2))
        for child in node:
            if child.tag == 'value' and child.get('name'):
                kwargs[child.get('name')] = _eval_xml(self, child, env)
            else:
                args.append(_eval_xml(self, child, env))
        # merge current context with context in kwargs
        kwargs['context'] = {**env.context, **kwargs.get('context', {})}
        # invoke method
        return odoo.api.call_kw(model, method_name, args, kwargs)
    elif node.tag == "test":
        return node.text


def str2bool(value):
    return value.lower() not in ('0', 'false', 'off')

def nodeattr2bool(node, attr, default=False):
    if not node.get(attr):
        return default
    val = node.get(attr).strip()
    if not val:
        return default
    return str2bool(val)

class xml_import(object):
    def get_env(self, node, eval_context=None):
        uid = node.get('uid')
        context = node.get('context')
        if uid or context:
            return self.env(
                user=uid and self.id_get(uid),
                context=context and {
                    **self.env.context,
                    **safe_eval(context, {
                        'ref': self.id_get,
                        **(eval_context or {})
                    })
                }
            )
        return self.env

    def make_xml_id(self, xml_id):
        if not xml_id or '.' in xml_id:
            return xml_id
        return "%s.%s" % (self.module, xml_id)

    def _test_xml_id(self, xml_id):
        if '.' in xml_id:
            module, id = xml_id.split('.', 1)
            assert '.' not in id, """The ID reference "%s" must contain
maximum one dot. They are used to refer to other modules ID, in the
form: module.record_id""" % (xml_id,)
            if module != self.module:
                modcnt = self.env['ir.module.module'].search_count([('name', '=', module), ('state', '=', 'installed')])
                assert modcnt == 1, """The ID "%s" refers to an uninstalled module""" % (xml_id,)

    def _tag_delete(self, rec):
        d_model = rec.get("model")
        records = self.env[d_model]

        d_search = rec.get("search")
        if d_search:
            idref = _get_idref(self, self.env, d_model, {})
            try:
                records = records.search(safe_eval(d_search, idref))
            except ValueError:
                _logger.warning('Skipping deletion for failed search `%r`', d_search, exc_info=True)

        d_id = rec.get("id")
        if d_id:
            try:
                records += records.browse(self.id_get(d_id))
            except ValueError:
                # d_id cannot be found. doesn't matter in this case
                _logger.warning('Skipping deletion for missing XML ID `%r`', d_id, exc_info=True)

        if records:
            records.unlink()

    def _tag_report(self, rec):
        res = {}
        for dest,f in (('name','string'),('model','model'),('report_name','name')):
            res[dest] = rec.get(f)
            assert res[dest], "Attribute %s of report is empty !" % (f,)
        for field, dest in (('attachment', 'attachment'),
                            ('attachment_use', 'attachment_use'),
                            ('usage', 'usage'),
                            ('file', 'report_file'),
                            ('report_type', 'report_type'),
                            ('parser', 'parser'),
                            ('print_report_name', 'print_report_name'),
                            ):
            if rec.get(field):
                res[dest] = rec.get(field)
        if rec.get('auto'):
            res['auto'] = safe_eval(rec.get('auto','False'))
        if rec.get('header'):
            res['header'] = safe_eval(rec.get('header','False'))

        res['multi'] = rec.get('multi') and safe_eval(rec.get('multi','False'))

        xml_id = rec.get('id','')
        self._test_xml_id(xml_id)
        warnings.warn(f"The <report> tag is deprecated, use a <record> tag for {xml_id!r}.", DeprecationWarning)

        if rec.get('groups'):
            g_names = rec.get('groups','').split(',')
            groups_value = []
            for group in g_names:
                if group.startswith('-'):
                    group_id = self.id_get(group[1:])
                    groups_value.append(odoo.Command.unlink(group_id))
                else:
                    group_id = self.id_get(group)
                    groups_value.append(odoo.Command.link(group_id))
            res['groups_id'] = groups_value
        if rec.get('paperformat'):
            pf_name = rec.get('paperformat')
            pf_id = self.id_get(pf_name)
            res['paperformat_id'] = pf_id

        xid = self.make_xml_id(xml_id)
        data = dict(xml_id=xid, values=res, noupdate=self.noupdate)
        report = self.env['ir.actions.report']._load_records([data], self.mode == 'update')
        self.idref[xml_id] = report.id

        if not rec.get('menu') or safe_eval(rec.get('menu','False')):
            report.create_action()
        elif self.mode=='update' and safe_eval(rec.get('menu','False'))==False:
            # Special check for report having attribute menu=False on update
            report.unlink_action()
        return report.id

    def _tag_function(self, rec):
        if self.noupdate and self.mode != 'init':
            return
        env = self.get_env(rec)
        _eval_xml(self, rec, env)

    def _tag_act_window(self, rec):
        name = rec.get('name')
        xml_id = rec.get('id','')
        self._test_xml_id(xml_id)
        warnings.warn(f"The <act_window> tag is deprecated, use a <record> for {xml_id!r}.", DeprecationWarning)
        view_id = False
        if rec.get('view_id'):
            view_id = self.id_get(rec.get('view_id'))
        domain = rec.get('domain') or '[]'
        res_model = rec.get('res_model')
        binding_model = rec.get('binding_model')
        view_mode = rec.get('view_mode') or 'tree,form'
        usage = rec.get('usage')
        limit = rec.get('limit')
        uid = self.env.user.id

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

        # Include all locals() in eval_context, for backwards compatibility
        eval_context = {
            'name': name,
            'xml_id': xml_id,
            'type': 'ir.actions.act_window',
            'view_id': view_id,
            'domain': domain,
            'res_model': res_model,
            'src_model': binding_model,
            'view_mode': view_mode,
            'usage': usage,
            'limit': limit,
            'uid': uid,
            'active_id': active_id,
            'active_ids': active_ids,
            'active_model': active_model,
        }
        context = self.get_env(rec, eval_context).context

        try:
            domain = safe_eval(domain, eval_context)
        except (ValueError, NameError):
            # Some domains contain references that are only valid at runtime at
            # client-side, so in that case we keep the original domain string
            # as it is. We also log it, just in case.
            _logger.debug('Domain value (%s) for element with id "%s" does not parse '\
                'at server-side, keeping original string, in case it\'s meant for client side only',
                domain, xml_id or 'n/a', exc_info=True)
        res = {
            'name': name,
            'type': 'ir.actions.act_window',
            'view_id': view_id,
            'domain': domain,
            'context': context,
            'res_model': res_model,
            'view_mode': view_mode,
            'usage': usage,
            'limit': limit,
        }

        if rec.get('groups'):
            g_names = rec.get('groups','').split(',')
            groups_value = []
            for group in g_names:
                if group.startswith('-'):
                    group_id = self.id_get(group[1:])
                    groups_value.append(odoo.Command.unlink(group_id))
                else:
                    group_id = self.id_get(group)
                    groups_value.append(odoo.Command.link(group_id))
            res['groups_id'] = groups_value

        if rec.get('target'):
            res['target'] = rec.get('target','')
        if binding_model:
            res['binding_model_id'] = self.env['ir.model']._get(binding_model).id
            res['binding_type'] = rec.get('binding_type') or 'action'
            views = rec.get('binding_views')
            if views is not None:
                res['binding_view_types'] = views
        xid = self.make_xml_id(xml_id)
        data = dict(xml_id=xid, values=res, noupdate=self.noupdate)
        self.env['ir.actions.act_window']._load_records([data], self.mode == 'update')

    def _tag_menuitem(self, rec, parent=None):
        rec_id = rec.attrib["id"]
        self._test_xml_id(rec_id)

        # The parent attribute was specified, if non-empty determine its ID, otherwise
        # explicitly make a top-level menu
        values = {
            'parent_id': False,
            'active': nodeattr2bool(rec, 'active', default=True),
        }

        if rec.get('sequence'):
            values['sequence'] = int(rec.get('sequence'))

        if parent is not None:
            values['parent_id'] = parent
        elif rec.get('parent'):
            values['parent_id'] = self.id_get(rec.attrib['parent'])
        elif rec.get('web_icon'):
            values['web_icon'] = rec.attrib['web_icon']


        if rec.get('name'):
            values['name'] = rec.attrib['name']

        if rec.get('action'):
            a_action = rec.attrib['action']

            if '.' not in a_action:
                a_action = '%s.%s' % (self.module, a_action)
            act = self.env.ref(a_action).sudo()
            values['action'] = "%s,%d" % (act.type, act.id)

            if not values.get('name') and act.type.endswith(('act_window', 'wizard', 'url', 'client', 'server')) and act.name:
                values['name'] = act.name

        if not values.get('name'):
            values['name'] = rec_id or '?'


        groups = []
        for group in rec.get('groups', '').split(','):
            if group.startswith('-'):
                group_id = self.id_get(group[1:])
                groups.append(odoo.Command.unlink(group_id))
            elif group:
                group_id = self.id_get(group)
                groups.append(odoo.Command.link(group_id))
        if groups:
            values['groups_id'] = groups


        data = {
            'xml_id': self.make_xml_id(rec_id),
            'values': values,
            'noupdate': self.noupdate,
        }
        menu = self.env['ir.ui.menu']._load_records([data], self.mode == 'update')
        for child in rec.iterchildren('menuitem'):
            self._tag_menuitem(child, parent=menu.id)

    def _tag_record(self, rec, extra_vals=None):
        rec_model = rec.get("model")
        env = self.get_env(rec)
        rec_id = rec.get("id", '')

        model = env[rec_model]

        if self.xml_filename and rec_id:
            model = model.with_context(
                install_module=self.module,
                install_filename=self.xml_filename,
                install_xmlid=rec_id,
            )

        self._test_xml_id(rec_id)
        xid = self.make_xml_id(rec_id)

        # in update mode, the record won't be updated if the data node explicitly
        # opt-out using @noupdate="1". A second check will be performed in
        # model._load_records() using the record's ir.model.data `noupdate` field.
        if self.noupdate and self.mode != 'init':
            # check if the xml record has no id, skip
            if not rec_id:
                return None

            record = env['ir.model.data']._load_xmlid(xid)
            for child in rec.xpath('.//record[@id]'):
                sub_xid = child.get("id")
                self._test_xml_id(sub_xid)
                sub_xid = self.make_xml_id(sub_xid)
                sub_record = env['ir.model.data']._load_xmlid(sub_xid)
                if sub_record:
                    self.idref[sub_xid] = sub_record.id

            if record:
                # if the resource already exists, don't update it but store
                # its database id (can be useful)
                self.idref[rec_id] = record.id
                return None
            elif not nodeattr2bool(rec, 'forcecreate', True):
                # if it doesn't exist and we shouldn't create it, skip it
                return None
            # else create it normally

        if xid and xid.partition('.')[0] != self.module:
            # updating a record created by another module
            record = self.env['ir.model.data']._load_xmlid(xid)
            if not record:
                if self.noupdate and not nodeattr2bool(rec, 'forcecreate', True):
                    # if it doesn't exist and we shouldn't create it, skip it
                    return None
                raise Exception("Cannot update missing record %r" % xid)

        res = {}
        sub_records = []
        for field in rec.findall('./field'):
            #TODO: most of this code is duplicated above (in _eval_xml)...
            f_name = field.get("name")
            f_ref = field.get("ref")
            f_search = field.get("search")
            f_model = field.get("model")
            if not f_model and f_name in model._fields:
                f_model = model._fields[f_name].comodel_name
            f_use = field.get("use",'') or 'id'
            f_val = False

            if f_search:
                idref2 = _get_idref(self, env, f_model, self.idref)
                q = safe_eval(f_search, idref2)
                assert f_model, 'Define an attribute model="..." in your .XML file !'
                # browse the objects searched
                s = env[f_model].search(q)
                # column definitions of the "local" object
                _fields = env[rec_model]._fields
                # if the current field is many2many
                if (f_name in _fields) and _fields[f_name].type == 'many2many':
                    f_val = [odoo.Command.set([x[f_use] for x in s])]
                elif len(s):
                    # otherwise (we are probably in a many2one field),
                    # take the first element of the search
                    f_val = s[0][f_use]
            elif f_ref:
                if f_name in model._fields and model._fields[f_name].type == 'reference':
                    val = self.model_id_get(f_ref)
                    f_val = val[0] + ',' + str(val[1])
                else:
                    f_val = self.id_get(f_ref, raise_if_not_found=nodeattr2bool(rec, 'forcecreate', True))
                    if not f_val:
                        _logger.warning("Skipping creation of %r because %s=%r could not be resolved", xid, f_name, f_ref)
                        return None
            else:
                f_val = _eval_xml(self, field, env)
                if f_name in model._fields:
                    field_type = model._fields[f_name].type
                    if field_type == 'many2one':
                        f_val = int(f_val) if f_val else False
                    elif field_type == 'integer':
                        f_val = int(f_val)
                    elif field_type in ('float', 'monetary'):
                        f_val = float(f_val)
                    elif field_type == 'boolean' and isinstance(f_val, str):
                        f_val = str2bool(f_val)
                    elif field_type == 'one2many':
                        for child in field.findall('./record'):
                            sub_records.append((child, model._fields[f_name].inverse_name))
                        if isinstance(f_val, str):
                            # We do not want to write on the field since we will write
                            # on the childrens' parents later
                            continue
                    elif field_type == 'html':
                        if field.get('type') == 'xml':
                            _logger.warning('HTML field %r is declared as `type="xml"`', f_name)
            res[f_name] = f_val
        if extra_vals:
            res.update(extra_vals)

        data = dict(xml_id=xid, values=res, noupdate=self.noupdate)
        record = model._load_records([data], self.mode == 'update')
        if rec_id:
            self.idref[rec_id] = record.id
        if config.get('import_partial'):
            env.cr.commit()
        for child_rec, inverse_name in sub_records:
            self._tag_record(child_rec, extra_vals={inverse_name: record.id})
        return rec_model, record.id

    def _tag_template(self, el):
        # This helper transforms a <template> element into a <record> and forwards it
        tpl_id = el.get('id', el.get('t-name'))
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

        if self.module.startswith('theme_'):
            model = 'theme.ir.ui.view'
        else:
            model = 'ir.ui.view'

        record_attrs = {
            'id': tpl_id,
            'model': model,
        }
        for att in ['forcecreate', 'context']:
            if att in el.attrib:
                record_attrs[att] = el.attrib.pop(att)

        Field = builder.E.field
        name = el.get('name', tpl_id)

        record = etree.Element('record', attrib=record_attrs)
        record.append(Field(name, name='name'))
        record.append(Field(full_tpl_id, name='key'))
        record.append(Field("qweb", name='type'))
        if 'track' in el.attrib:
            record.append(Field(el.get('track'), name='track'))
        if 'priority' in el.attrib:
            record.append(Field(el.get('priority'), name='priority'))
        if 'inherit_id' in el.attrib:
            record.append(Field(name='inherit_id', ref=el.get('inherit_id')))
        if 'website_id' in el.attrib:
            record.append(Field(name='website_id', ref=el.get('website_id')))
        if 'key' in el.attrib:
            record.append(Field(el.get('key'), name='key'))
        if el.get('active') in ("True", "False"):
            view_id = self.id_get(tpl_id, raise_if_not_found=False)
            if self.mode != "update" or not view_id:
                record.append(Field(name='active', eval=el.get('active')))
        if el.get('customize_show') in ("True", "False"):
            record.append(Field(name='customize_show', eval=el.get('customize_show')))
        groups = el.attrib.pop('groups', None)
        if groups:
            grp_lst = [("ref('%s')" % x) for x in groups.split(',')]
            record.append(Field(name="groups_id", eval="[Command.set(["+', '.join(grp_lst)+"])]"))
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

        return self._tag_record(record)

    def id_get(self, id_str, raise_if_not_found=True):
        if id_str in self.idref:
            return self.idref[id_str]
        res = self.model_id_get(id_str, raise_if_not_found)
        return res and res[1]

    def model_id_get(self, id_str, raise_if_not_found=True):
        if '.' not in id_str:
            id_str = '%s.%s' % (self.module, id_str)
        return self.env['ir.model.data']._xmlid_to_res_model_res_id(id_str, raise_if_not_found=raise_if_not_found)

    def _tag_root(self, el):
        for rec in el:
            f = self._tags.get(rec.tag)
            if f is None:
                continue

            self.envs.append(self.get_env(el))
            self._noupdate.append(nodeattr2bool(el, 'noupdate', self.noupdate))
            try:
                f(rec)
            except ParseError:
                raise
            except ValidationError as err:
                msg = "while parsing {file}:{viewline}\n{err}\n\nView error context:\n{context}\n".format(
                    file=rec.getroottree().docinfo.URL,
                    viewline=rec.sourceline,
                    context=pprint.pformat(getattr(err, 'context', None) or '-no context-'),
                    err=err.args[0],
                )
                _logger.debug(msg, exc_info=True)
                raise ParseError(msg) from None  # Restart with "--log-handler odoo.tools.convert:DEBUG" for complete traceback
            except Exception as e:
                raise ParseError('while parsing %s:%s, somewhere inside\n%s' % (
                    rec.getroottree().docinfo.URL,
                    rec.sourceline,
                    etree.tostring(rec, encoding='unicode').rstrip()
                )) from e
            finally:
                self._noupdate.pop()
                self.envs.pop()

    @property
    def env(self):
        return self.envs[-1]

    @property
    def noupdate(self):
        return self._noupdate[-1]

    def __init__(self, cr, module, idref, mode, noupdate=False, xml_filename=None):
        self.mode = mode
        self.module = module
        self.envs = [odoo.api.Environment(cr, SUPERUSER_ID, {})]
        self.idref = {} if idref is None else idref
        self._noupdate = [noupdate]
        self.xml_filename = xml_filename
        self._tags = {
            'record': self._tag_record,
            'delete': self._tag_delete,
            'function': self._tag_function,
            'menuitem': self._tag_menuitem,
            'template': self._tag_template,
            'report': self._tag_report,
            'act_window': self._tag_act_window,

            **dict.fromkeys(self.DATA_ROOTS, self._tag_root)
        }

    def parse(self, de):
        assert de.tag in self.DATA_ROOTS, "Root xml tag must be <openerp>, <odoo> or <data>."
        self._tag_root(de)
    DATA_ROOTS = ['odoo', 'data', 'openerp']

def convert_file(cr, module, filename, idref, mode='update', noupdate=False, kind=None, pathname=None):
    if pathname is None:
        pathname = os.path.join(module, filename)
    ext = os.path.splitext(filename)[1].lower()

    with file_open(pathname, 'rb') as fp:
        if ext == '.csv':
            convert_csv_import(cr, module, pathname, fp.read(), idref, mode, noupdate)
        elif ext == '.sql':
            convert_sql_import(cr, fp)
        elif ext == '.xml':
            convert_xml_import(cr, module, fp, idref, mode, noupdate)
        elif ext == '.js':
            pass # .js files are valid but ignored here.
        else:
            raise ValueError("Can't load unknown file type %s.", filename)

def convert_sql_import(cr, fp):
    cr.execute(fp.read()) # pylint: disable=sql-injection

def convert_csv_import(cr, module, fname, csvcontent, idref=None, mode='init',
        noupdate=False):
    '''Import csv file :
        quote: "
        delimiter: ,
        encoding: utf-8'''
    filename, _ext = os.path.splitext(os.path.basename(fname))
    model = filename.split('-')[0]
    reader = pycompat.csv_reader(io.BytesIO(csvcontent), quotechar='"', delimiter=',')
    fields = next(reader)

    if not (mode == 'init' or 'id' in fields):
        _logger.error("Import specification does not contain 'id' and we are in init mode, Cannot continue.")
        return

    # filter out empty lines (any([]) == False) and lines containing only empty cells
    datas = [
        line for line in reader
        if any(line)
    ]

    context = {
        'mode': mode,
        'module': module,
        'install_module': module,
        'install_filename': fname,
        'noupdate': noupdate,
    }
    env = odoo.api.Environment(cr, SUPERUSER_ID, context)
    result = env[model].load(fields, datas)
    if any(msg['type'] == 'error' for msg in result['messages']):
        # Report failed import and abort module install
        warning_msg = "\n".join(msg['message'] for msg in result['messages'])
        raise Exception(_('Module loading %s failed: file %s could not be processed:\n %s') % (module, fname, warning_msg))

def convert_xml_import(cr, module, xmlfile, idref=None, mode='init', noupdate=False, report=None):
    doc = etree.parse(xmlfile)
    schema = os.path.join(config['root_path'], 'import_xml.rng')
    relaxng = etree.RelaxNG(etree.parse(schema))
    try:
        relaxng.assert_(doc)
    except Exception:
        _logger.exception("The XML file '%s' does not fit the required schema !", xmlfile.name)
        if jingtrang:
            p = subprocess.run(['pyjing', schema, xmlfile.name], stdout=subprocess.PIPE)
            _logger.warning(p.stdout.decode())
        else:
            for e in relaxng.error_log:
                _logger.warning(e)
            _logger.info("Install 'jingtrang' for more precise and useful validation messages.")
        raise

    if isinstance(xmlfile, str):
        xml_filename = xmlfile
    else:
        xml_filename = xmlfile.name
    obj = xml_import(cr, module, idref, mode, noupdate=noupdate, xml_filename=xml_filename)
    obj.parse(doc.getroot())
