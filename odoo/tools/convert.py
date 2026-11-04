# Part of Odoo. See LICENSE file for full copyright and licensing details.

__all__ = [
    'convert_file',
]
import csv
import io
import json
import logging
import os.path
import pprint
import re
import subprocess
import typing
import warnings
import zoneinfo
from datetime import datetime, timedelta, UTC, tzinfo

import psycopg2.extensions
from dateutil.relativedelta import relativedelta
from lxml import etree, builder
from psycopg2.extras import Json as PsycopgJson
try:
    import jingtrang
except ImportError:
    jingtrang = None

from .binary import BinaryBytes
from .config import config
from .constants import IN_MAX
from .misc import file_open, file_path, split_every, SKIPPED_ELEMENT_TYPES
from .sql import SQL
from .safe_eval import _UNSAFE_ATTRIBUTES
from odoo.exceptions import ValidationError

from .safe_eval import safe_eval, time

_logger = logging.getLogger(__name__)

ConvertMode = typing.Literal['init', 'update']
IdRef = dict[str, int | typing.Literal[False]]


class Pytz(typing.NamedTuple):
    timezone: typing.Callable[[str], zoneinfo.ZoneInfo]
    utc: tzinfo
    UTC: tzinfo


class ParseError(Exception):
    ...


def _get_eval_context(self, env, model_str):
    from odoo import fields, release  # noqa: PLC0415
    context = dict(Command=fields.Command,
                  time=time,
                  DateTime=datetime,
                  datetime=datetime,
                  timedelta=timedelta,
                  relativedelta=relativedelta,
                  version=release.major_version,
                  ref=self.id_get,
                  pytz=Pytz(zoneinfo.ZoneInfo, UTC, UTC))
    if model_str:
        context['obj'] = env[model_str].browse
    return context

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
        if f_search := node.get('search'):
            f_use = node.get("use",'id')
            f_name = node.get("name")
            context = _get_eval_context(self, env, f_model)
            q = safe_eval(f_search, context)
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
        if a_eval := node.get('eval'):
            context = _get_eval_context(self, env, f_model)
            try:
                return safe_eval(a_eval, context)
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
                rec_id = m[1]
                xid = self.make_xml_id(rec_id)
                if (record_id := self.idref.get(xid)) is None:
                    record_id = self.idref[xid] = self.id_get(xid)
                # So funny story: in Python 3, bytes(n: int) returns a
                # bytestring of n nuls. In Python 2 it obviously returns the
                # stringified number, which is what we're expecting here
                s = s.replace(found, str(record_id))
            s = s.replace('%%', '%') # Quite weird but it's for (somewhat) backward compatibility sake
            return s

        if t == 'xml':
            _fix_multiple_roots(node)
            return '<?xml version="1.0"?>\n'\
                +_process("".join(etree.tostring(n, encoding='unicode') for n in node))
        if t == 'html':
            return _process("".join(etree.tostring(n, method='html', encoding='unicode') for n in node))

        if node.get('file'):
            node_file = node.get('file')
            if t == 'bytes':
                with file_open(node_file, 'rb', env=env) as f:
                    return BinaryBytes(f.read())
            if t == 'base64':
                warnings.warn("Since 20.0, use type=bytes instead of type=base64", DeprecationWarning)
                with file_open(node_file, 'rb', env=env) as f:
                    return BinaryBytes(f.read()).to_base64()

            with file_open(node_file, env=env) as f:
                data = f.read()
        else:
            data = node.text or ''

        match t:
            case 'file':
                path = data.strip()
                try:
                    file_path(os.path.join(self.module, path))
                except FileNotFoundError:
                    raise FileNotFoundError(
                        f"No such file or directory: {path!r} in {self.module}"
                    ) from None
                return '%s,%s' % (self.module, path)
            case 'char':
                return data
            case 'int':
                d = data.strip()
                if d == 'None':
                    return None
                return int(d)
            case 'float':
                return float(data.strip())
            case 'list':
                return [_eval_xml(self, n, env) for n in node.iterchildren('value')]
            case 'tuple':
                return tuple(_eval_xml(self, n, env) for n in node.iterchildren('value'))
            case 'bytes':
                raise ValueError("bytes type is only compatible with file data")
            case 'base64':
                raise ValueError("base64 type is only compatible with file data")
            case t:
                raise ValueError(f"Unknown type {t!r}")

    elif node.tag == "function":
        from odoo.models import BaseModel  # noqa: PLC0415
        model_str = node.get('model')
        model = env[model_str]
        method_name = node.get('name') or ''
        if '__' in method_name or method_name in _UNSAFE_ATTRIBUTES:
            raise NameError(f'Access to forbidden name {method_name!r}')
        # determine arguments
        args = []
        kwargs = {}

        if a_eval := node.get('eval'):
            context = _get_eval_context(self, env, model_str)
            args = list(safe_eval(a_eval, context))
        for child in node:
            if child.tag == 'value' and child.get('name'):
                kwargs[child.get('name')] = _eval_xml(self, child, env)
            else:
                args.append(_eval_xml(self, child, env))
        # merge current context with context in kwargs
        if 'context' in kwargs:
            model = model.with_context(**kwargs.pop('context'))
        method = getattr(model, method_name)
        is_model_method = getattr(method, '_api_model', False)
        if is_model_method:
            pass  # already bound to an empty recordset
        else:
            record_ids, *args = args
            # skip falsy ids
            try:
                record_ids = tuple(record_id for record_id in record_ids if record_id)
            except TypeError:
                record_ids = (record_ids,) if record_ids else ()
            model = model.browse(record_ids)
            method = getattr(model, method_name)
        # invoke method
        result = method(*args, **kwargs)
        if isinstance(result, BaseModel):
            result = result.ids
        return result
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
                    }),
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

        if d_search := rec.get("search"):
            context = _get_eval_context(self, self.env, d_model)
            try:
                records = records.search(safe_eval(d_search, context))
            except ValueError:
                _logger.warning('Skipping deletion for failed search `%r`', d_search, exc_info=True)

        if d_id := rec.get("id"):
            try:
                records += records.browse(self.id_get(d_id))
            except ValueError:
                # d_id cannot be found. doesn't matter in this case
                _logger.warning('Skipping deletion for missing XML ID `%r`', d_id, exc_info=True)

        if records:
            records.unlink()

    def _tag_function(self, rec):
        if self.noupdate and self.mode != 'init':
            return
        env = self.get_env(rec)
        _eval_xml(self, rec, env)

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

        from odoo.fields import Command  # noqa: PLC0415
        groups = []
        for group in rec.get('groups', '').split(','):
            if group.startswith('-'):
                group_id = self.id_get(group[1:])
                groups.append(Command.unlink(group_id))
            elif group:
                group_id = self.id_get(group)
                groups.append(Command.link(group_id))
        if groups:
            values['group_ids'] = groups


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
                install_mode=True,
                install_module=self.module,
                install_filename=self.xml_filename,
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

            if record := env['ir.model.data']._load_xmlid(xid):
                for child in rec.xpath('.//record[@id]'):
                    sub_xid = child.get("id")
                    self._test_xml_id(sub_xid)
                    sub_xid = self.make_xml_id(sub_xid)
                    if sub_record := env['ir.model.data']._load_xmlid(sub_xid):
                        self.idref[sub_xid] = sub_record.id

                # if the resource already exists, don't update it but store
                # its database id (can be useful)
                self.idref[xid] = record.id
                return None
            elif not nodeattr2bool(rec, 'forcecreate', True):
                # if it doesn't exist and we shouldn't create it, skip it
                return None
            # else create it normally

        foreign_record_to_create = False
        if xid and xid.partition('.')[0] != self.module:
            # updating a record created by another module
            record = self.env['ir.model.data']._load_xmlid(xid)
            if not record and not (foreign_record_to_create := nodeattr2bool(rec, 'forcecreate')):  # Allow foreign records if explicitely stated
                if self.noupdate and not nodeattr2bool(rec, 'forcecreate', True):
                    # if it doesn't exist and we shouldn't create it, skip it
                    return None
                raise Exception("Cannot update missing record %r" % xid)

        from odoo.fields import Command  # noqa: PLC0415
        res = {}
        sub_records = []
        for field in rec.iterchildren('field'):
            #TODO: most of this code is duplicated above (in _eval_xml)...
            f_name = field.get("name")
            if '@' in f_name:
                continue  # used for translations
            f_model = field.get("model")
            if not f_model and f_name in model._fields and model._fields[f_name].relational:
                f_model = model._fields[f_name].comodel_name
            f_use = field.get("use",'') or 'id'
            f_val = False

            if f_search := field.get("search"):
                assert f_model, 'Define an attribute model="..." in your .XML file!'
                context = _get_eval_context(self, env, f_model)
                q = safe_eval(f_search, context)
                # browse the objects searched
                s = env[f_model].search(q)
                # column definitions of the "local" object
                _fields = env[rec_model]._fields
                # if the current field is many2many
                if (f_name in _fields) and _fields[f_name].type == 'many2many':
                    f_val = [Command.set([x[f_use] for x in s])]
                elif len(s):
                    # otherwise (we are probably in a many2one field),
                    # take the first element of the search
                    f_val = s[0][f_use]
            elif f_ref := field.get("ref"):
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
                        for child in field.iterchildren('record'):
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
        if 'sequence' not in res and 'sequence' in model._fields:
            sequence = self.next_sequence()
            if sequence:
                res['sequence'] = sequence
        if 'xmlid' not in res and 'xmlid' in model._fields:
            res['xmlid'] = xid

        data = dict(xml_id=xid, values=res, noupdate=self.noupdate)
        if foreign_record_to_create:
            model = model.with_context(foreign_record_to_create=foreign_record_to_create)
        record = model._load_records([data], self.mode == 'update')
        if xid:
            self.idref[xid] = record.id
        if config.get('import_partial'):
            env.cr.commit()
        for child_rec, inverse_name in sub_records:
            self._tag_record(child_rec, extra_vals={inverse_name: record.id})
        return rec_model, record.id

    def _tag_template(self, el):
        # This helper transforms a <template> element into a <record> and forwards it
        tpl_id = el.get('id', el.get('t-name'))
        full_tpl_id = tpl_id
        attrib = el.attrib
        if '.' not in full_tpl_id:
            full_tpl_id = '%s.%s' % (self.module, tpl_id)
        # set the full template name for qweb <module>.<id>
        if not el.get('inherit_id'):
            el.set('t-name', full_tpl_id)
            el.tag = 't'
        else:
            el.tag = 'data'
        attrib.pop('id', None)

        if self.module.startswith('theme_'):
            model = 'theme.ir.ui.view'
        else:
            model = 'ir.ui.view'

        record_attrs = {
            'id': tpl_id,
            'model': model,
        }
        for att in ['forcecreate', 'context']:
            if att in attrib:
                record_attrs[att] = attrib.pop(att)

        Field = builder.E.field
        name = el.get('name', tpl_id)

        record = etree.Element('record', attrib=record_attrs)
        record.append(Field(name, name='name'))
        record.append(Field(full_tpl_id, name='key'))
        record.append(Field("qweb", name='type'))
        if 'track' in attrib:
            record.append(Field(attrib.pop('track'), name='track'))
        if 'priority' in attrib:
            record.append(Field(attrib.pop('priority'), name='priority'))
        if 'inherit_id' in attrib:
            record.append(Field(name='inherit_id', ref=attrib.pop('inherit_id')))
        if 'technical_usage' in attrib:
            record.append(Field(attrib.pop('technical_usage'), name='technical_usage'))
        if 'website_id' in attrib:
            record.append(Field(name='website_id', ref=attrib.pop('website_id')))
        if 'key' in attrib:
            record.append(Field(attrib.pop('key'), name='key'))

        # If the "active" value is set on the root node (instead of an inner
        # <field>), it is treated as the value for the "active" field but only
        # when *not updating*. This allows to update the record in a more recent
        # version without changing its active state (compatibility).
        if (active := attrib.pop('active', None)) in ("True", "False"):
            view_id = self.id_get(tpl_id, raise_if_not_found=False)
            if self.mode != "update" or not view_id:
                record.append(Field(name='active', eval=active))

        if (customize_show := attrib.pop('customize_show', None)) in ("True", "False"):
            record.append(Field(name='customize_show', eval=customize_show))
        groups = attrib.pop('groups', None)
        if groups:
            grp_lst = [("ref('%s')" % x) for x in groups.split(',')]
            record.append(Field(name="group_ids", eval="[Command.set(["+', '.join(grp_lst)+"])]"))
        if attrib.pop('primary', None) == 'True':
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

    def _tag_asset(self, el):
        """
        Transforms an <asset> element into a <record> and forwards it.
        """
        asset_id = el.get('id')
        Field = builder.E.field

        record = etree.Element('record', attrib={
            'id': asset_id,
            'model': 'theme.ir.asset' if self.module.startswith('theme_') else 'ir.asset',
        })

        name = el.get('name', asset_id)
        record.append(Field(name, name='name'))

        # E.g. <bundle directive="prepend">web.assets_frontend</bundle>
        # (directive is optional)
        bundle_el = el.find('bundle')
        record.append(Field(bundle_el.text, name='bundle'))
        if 'directive' in bundle_el.attrib:
            record.append(Field(bundle_el.get('directive'), name='directive'))

        # E.g. <path>website/static/src/snippets/s_share/000.scss</path>
        record.append(Field(el.find('path').text, name='path'))

        # Same as <template> for ir.ui.view:
        # If the "active" value is set on the root node (instead of an inner
        # <field>), it is treated as the value for the "active" field but only
        # when *not updating*. This allows to update the record in a more recent
        # version without changing its active state (compatibility).
        if el.get('active') in ("True", "False"):
            record_id = self.id_get(asset_id, raise_if_not_found=False)
            if self.mode != "update" or not record_id:
                record.append(Field(name='active', eval=el.get('active')))

        for child in el.iterchildren('field'):
            record.append(child)

        return self._tag_record(record)

    def id_get(self, id_str, raise_if_not_found=True):
        id_str = self.make_xml_id(id_str)
        if id_str in self.idref:
            return self.idref[id_str]
        return self.model_id_get(id_str, raise_if_not_found)[1]

    def model_id_get(self, id_str, raise_if_not_found=True):
        id_str = self.make_xml_id(id_str)
        return self.env['ir.model.data']._xmlid_to_res_model_res_id(id_str, raise_if_not_found=raise_if_not_found)

    def _tag_root(self, el):
        for rec in el:
            f = self._tags.get(rec.tag)
            if f is None:
                continue

            self.envs.append(self.get_env(el))
            self._noupdate.append(nodeattr2bool(el, 'noupdate', self.noupdate))
            self._sequences.append(0 if nodeattr2bool(el, 'auto_sequence', False) else None)
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
                self._sequences.pop()

    @property
    def env(self):
        return self.envs[-1]

    @property
    def noupdate(self):
        return self._noupdate[-1]

    def next_sequence(self):
        value = self._sequences[-1]
        if value is not None:
            value = self._sequences[-1] = value + 10
        return value

    def __init__(self, env, module, idref: IdRef | None, mode: ConvertMode, noupdate: bool = False, xml_filename: str = ''):
        self.mode = mode
        self.module = module
        self.envs = [env(context=dict(env.context, lang=None))]
        self.idref: IdRef = {} if idref is None else idref
        self._noupdate = [noupdate]
        self._sequences = []
        self.xml_filename = xml_filename
        self._tags = {
            'record': self._tag_record,
            'delete': self._tag_delete,
            'function': self._tag_function,
            'menuitem': self._tag_menuitem,
            'template': self._tag_template,
            'asset': self._tag_asset,

            **dict.fromkeys(self.DATA_ROOTS, self._tag_root)
        }

    def parse(self, de):
        assert de.tag in self.DATA_ROOTS, "Root xml tag must be <openerp>, <odoo> or <data>."
        self._tag_root(de)
    DATA_ROOTS = ['odoo', 'data', 'openerp']


def convert_file(
        env,
        module,
        filename,
        idref: IdRef | None,
        mode: ConvertMode = 'update',
        noupdate=False,
        kind=None,
        pathname=None,
):
    if kind is not None:
        warnings.warn(
            "The `kind` argument is deprecated in Odoo 19.",
            DeprecationWarning,
            stacklevel=2,
        )
    if pathname is None:
        pathname = os.path.join(module, filename)
    ext = os.path.splitext(filename)[1].lower()

    with file_open(pathname, 'rb', env=env) as fp:
        if ext == '.csv':
            convert_csv_import(env, module, pathname, fp.read(), idref, mode, noupdate)
        elif ext == '.sql':
            env.cr.execute(fp.read())  # pylint: disable=sql-injection
        elif ext == '.xml':
            convert_xml_import(env, module, fp, idref, mode, noupdate)
        elif ext == '.js':
            pass # .js files are valid but ignored here.
        else:
            raise ValueError("Can't load unknown file type %s.", filename)


def convert_csv_import(
        env,
        module,
        fname,
        csvcontent,
        idref: IdRef | None = None,
        mode: ConvertMode = 'init',
        noupdate=False,
):
    '''Import csv file :
        quote: "
        delimiter: ,
        encoding: utf-8'''
    env = env(context=dict(env.context, lang=None))
    filename, _ext = os.path.splitext(os.path.basename(fname))
    model = filename.split('-')[0]
    reader = csv.reader(io.StringIO(csvcontent.decode()), quotechar='"', delimiter=',')
    fields = next(reader)

    if not (mode == 'init' or 'id' in fields):
        _logger.error("Import specification does not contain 'id' and we are in init mode, Cannot continue.")
        return

    translate_indexes = {i for i, field in enumerate(fields) if '@' in field}
    def remove_translations(row):
        return [cell for i, cell in enumerate(row) if i not in translate_indexes]

    fields = remove_translations(fields)
    if not fields:
        return

    # clean the data from translations (treated during translation import), then
    # filter out empty lines (any([]) == False) and lines containing only empty cells
    datas = [
        data_line for line in reader
        if any(data_line := remove_translations(line))
    ]

    context = {
        'mode': mode,
        'module': module,
        'install_mode': True,
        'install_module': module,
        'install_filename': fname,
        'noupdate': noupdate,
    }
    if _bulk_load_csv(env[model].with_context(**context), module, fields, datas, mode == 'update', noupdate):
        return
    result = env[model].with_context(**context).load(fields, datas)
    if any(msg['type'] == 'error' for msg in result['messages']):
        # Report failed import and abort module install
        warning_msg = "\n".join(msg['message'] for msg in result['messages'])
        raise Exception(env._(
            "Module loading %(module)s failed: file %(file)s could not be processed:\n%(message)s",
            module=module,
            file=fname,
            message=warning_msg,
        ))


# Below this number of rows, the regular import is fast enough.
BULK_LOAD_MIN_ROWS = 1000
BULK_LOAD_FIELD_TYPES = frozenset({
    'boolean', 'char', 'date', 'float', 'integer', 'many2one', 'selection', 'text',
})
# methods of the regular import that are bypassed by the bulk load
BULK_LOAD_BYPASSED_METHODS = (
    'create', '_create', 'write', 'load', '_load_records', '_load_records_create', '_load_records_write',
)


def _bulk_load_csv(model, module, header, rows, update, noupdate):
    """ Fast path of :func:`convert_csv_import` for large files of simple records.

    The regular import converts and creates the records through ``load()``,
    which takes seconds for catalogs of tens of thousands of rows (product
    codes, cities, ...). When the model does not customize the creation of its
    records and all the columns are plain stored fields, the rows are converted
    like ``load()`` does, but once per distinct value, and inserted with
    ``COPY``; the ORM then processes the computed fields,
    the constraints and the external ids of the new records in batch. Existing
    records are only written when their values differ from the file.

    :return: whether the file has been loaded; when ``False``, nothing has been
        written and the regular import must be used
    """
    if len(rows) < BULK_LOAD_MIN_ROWS or not _bulk_load_supported_model(model):
        return False
    columns = _bulk_load_columns(model, header)
    if columns is None:
        return False
    id_index, fields = columns

    # convert the rows; anything unexpected is left to the regular import,
    # which also reports errors properly
    prefix = f'{module}.'
    xml_ids = []
    vals_list = []
    try:
        converters = _bulk_load_converters(model, module, fields, rows)
        for row in rows:
            xml_id = row[id_index]
            xml_ids.append(xml_id if '.' in xml_id else prefix + xml_id)
            vals_list.append({field.name: convert(row[index]) for index, field, convert in converters})
    except (IndexError, ValueError):
        return False
    if (
        len(set(xml_ids)) != len(xml_ids)
        or not all(xml_id.startswith(prefix) and xml_id != prefix for xml_id in xml_ids)
    ):
        return False

    imd = model.env['ir.model.data']
    existing = {
        f'{row_module}.{name}': (row_model, res_id, row_noupdate, record_id)
        for _id, row_module, name, row_model, res_id, row_noupdate, record_id
        in imd._lookup_xmlids(xml_ids, model)
    }
    if any(row_model != model._name or not record_id for row_model, _res_id, _noupdate, record_id in existing.values()):
        return False

    given_fnames = [field.name for _index, field in fields]
    defaults = {
        fname: value
        for fname, value in model._add_missing_default_values(dict.fromkeys(given_fnames, False)).items()
        if fname not in given_fnames
    }
    if any(not (field := model._fields[fname]).store or not field.column_type for fname in defaults):
        return False
    # the database would reject missing required values without a proper error
    # message; computed fields are left to the ORM, like create() does
    if any(
        field.required and field.store and field.column_type and not field.compute and fname not in given_fnames
        and field.convert_to_column_insert(defaults.get(fname, False), model) is None
        for fname, field in model._fields.items()
    ):
        return False

    to_create = []          # [(xml_id, vals)]
    to_check = {}           # {record_id: vals}
    for xml_id, vals in zip(xml_ids, vals_list):
        if not (row := existing.get(xml_id)):
            to_create.append((xml_id, vals))
        elif not (update and row[2]):
            to_check[row[1]] = vals

    model.env.flush_all()
    for record_id in _bulk_load_changed_ids(model, to_check):
        model.browse(record_id)._load_records_write(to_check[record_id])

    if to_create:
        ids = _bulk_load_create(model, to_create, defaults)
        # like _update_xmlids(), without its upsert and cache updates per row
        # as these external ids are known to be new
        imd.flush_model()
        model.env.execute_query(SQL(
            """ INSERT INTO ir_model_data (module, name, model, res_id, noupdate)
                SELECT %s, UNNEST(%s::varchar[]), %s, UNNEST(%s::int[]), %s """,
            module, [xml_id[len(prefix):] for xml_id, _vals in to_create], model._name, ids, bool(noupdate),
        ))
    # the existing external ids already target the right records
    if not model.pool.ready:
        model.pool.loaded_xmlids.update(xml_ids)
    _logger.debug(
        "%s: bulk loaded %d records, %d new", model.env.context.get('install_filename'), len(xml_ids), len(to_create),
    )
    return True


def _bulk_load_supported_model(model):
    # access rights and record rules are not checked
    if (
        not model.env.su
        or model._abstract or not model._auto or model._inherits or model._parent_store
        or model._check_company_auto or any(field.precompute for field in model._fields.values())
    ):
        return False
    # Generic overrides on 'base' are ignored, as they don't concern the
    # supported field types (html sanitization, ...), except for triggering the
    # cron filling AI fields, which runs daily anyway. The registry class is
    # included for the methods patched at runtime (automation rules).
    classes = [
        model.env.registry[model._name],
        *(
            cls for cls in model._model_classes__
            if not cls.__module__.startswith('odoo.orm.') and not (hasattr(cls, '_name') and cls._name == 'base')
        ),
    ]
    return not any(method in cls.__dict__ for cls in classes for method in BULK_LOAD_BYPASSED_METHODS)


def _bulk_load_columns(model, header):
    """ Return the index of the ``id`` column and the fields of the other
    columns as ``(id_index, [(index, field)])``, or ``None`` if a column cannot
    be bulk loaded.
    """
    from odoo.orm.models import LOG_ACCESS_COLUMNS, fix_import_export_id_paths  # noqa: PLC0415

    id_index = None
    fields = []
    for index, name in enumerate(header):
        fname, *subfield = fix_import_export_id_paths(name)
        if fname == 'id' and not subfield:
            id_index = index
            continue
        field = model._fields.get(fname)
        if (
            field is None
            or field.type not in BULK_LOAD_FIELD_TYPES
            or not field.store
            or not field.column_type
            or fname in LOG_ACCESS_COLUMNS
            or field.compute
            or field.inverse
            or field.company_dependent
            or callable(field.translate)
            or subfield != (['id'] if field.type == 'many2one' else [])
        ):
            return None
        fields.append((index, field))
    if id_index is None or len({field for _index, field in fields}) != len(fields):
        return None
    return id_index, fields


def _bulk_load_converters(model, module, fields, rows):
    """ Return the functions converting the CSV cells of the given columns to
    values for ``create()``, as ``[(index, field, convert)]``.

    They use ``ir.fields.converter`` like ``load()``, but convert each distinct
    value of a column once, and raise ``ValueError`` for the values on which
    ``load()`` would report an error or a warning.
    """
    env = model.env
    # fetch the records of the external ids of many2one columns in batch,
    # instead of one query per external id
    import_cache = {}
    for index, field in fields:
        if field.type == 'many2one':
            xml_ids = {value if '.' in value else f'{module}.{value}' for row in rows if (value := row[index])}
            for _id, xml_module, name, res_model, res_id, _noupdate, record_id in env['ir.model.data']._lookup_xmlids(
                xml_ids, env[field.comodel_name],
            ):
                if record_id:
                    import_cache[f'{xml_module}.{name}'] = (res_model, res_id)
    converter = env['ir.fields.converter'].with_context(import_cache=import_cache, _import_current_module=module)
    return [(index, field, _bulk_load_converter(converter, model, field)) for index, field in fields]


def _bulk_load_converter(converter, model, field):
    convert = converter.to_field(model, field, savepoint=None)
    many2one = field.type == 'many2one'
    cache = {}

    def convert_cached(value):
        if value not in cache:
            result = False
            if value:
                result, warnings = convert([{'id': value}] if many2one else value)
                if warnings:
                    raise ValueError(warnings)
            # the database would reject it without a proper error message
            if field.required and field.convert_to_column_insert(result, model) is None:
                raise ValueError(f"Missing required value for field {field.name!r}")
            cache[value] = result
        return cache[value]
    return convert_cached


def _bulk_load_changed_ids(model, vals_by_id):
    """ Return the ids in ``vals_by_id`` whose record differs from the given
    values in database.
    """
    if not vals_by_id:
        return []
    fields = [model._fields[fname] for fname in next(iter(vals_by_id.values()))]
    if not fields:
        return []

    def normalize(value):
        if isinstance(value, PsycopgJson):
            value = value.adapted
        if isinstance(value, dict):
            return value.get('en_US')
        return value or None

    changed = []
    for ids in split_every(IN_MAX, vals_by_id):
        for record_id, *db_values in model.env.execute_query(SQL(
            "SELECT id, %s FROM %s WHERE id IN %s",
            SQL(', ').join(SQL.identifier(field.name) for field in fields),
            SQL.identifier(model._table),
            tuple(ids),
        )):
            vals = vals_by_id[record_id]
            if any(
                normalize(db_value) != normalize(field.convert_to_column_insert(vals[field.name], model, vals))
                for field, db_value in zip(fields, db_values)
            ):
                changed.append(record_id)
    return changed


def _bulk_load_create(model, to_create, defaults):
    """ Insert the given records, and return their ids. """
    from odoo.orm.models import LOG_ACCESS_COLUMNS  # noqa: PLC0415

    env = model.env
    ids = [id_ for id_, in env.execute_query(SQL(
        "SELECT nextval(pg_get_serial_sequence(%s, 'id')) FROM generate_series(1, %s)",
        model._table, len(to_create),
    ))]

    def copy_value(value):
        if isinstance(value, PsycopgJson):
            return json.dumps(value.adapted)
        if isinstance(value, bool):
            return 't' if value else 'f'
        return value

    fields = [model._fields[fname] for fname in to_create[0][1]]
    constant_fnames = list(defaults)
    constant_values = [
        copy_value(model._fields[fname].convert_to_column_insert(value, model, defaults))
        for fname, value in defaults.items()
    ]
    if model._log_access:
        constant_fnames += LOG_ACCESS_COLUMNS
        constant_values += [env.uid, env.cr.now(), env.uid, env.cr.now()]

    buffer = io.StringIO()
    writer = csv.writer(buffer, quoting=csv.QUOTE_NOTNULL)
    for id_, (_xml_id, vals) in zip(ids, to_create):
        writer.writerow([
            id_,
            *(copy_value(field.convert_to_column_insert(vals[field.name], model, vals)) for field in fields),
            *constant_values,
        ])
    buffer.seek(0)
    query = env.cr.mogrify(SQL(
        "COPY %s (%s) FROM STDIN WITH (FORMAT csv)",
        SQL.identifier(model._table),
        SQL(', ').join(map(SQL.identifier, ['id', *(field.name for field in fields), *constant_fnames])),
    )).decode()
    # COPY is not compatible with async callbacks (gevent)
    callback = psycopg2.extensions.get_wait_callback()
    psycopg2.extensions.set_wait_callback(None)
    try:
        env.cr.copy_expert(query, buffer)
    finally:
        psycopg2.extensions.set_wait_callback(callback)
    env.transaction._wrote__ = True

    # the inverses of many2one fields don't know about the new records
    fnames = [*(field.name for field in fields), *defaults]
    for fname in fnames:
        for inverse in env.registry.field_inverses[model._fields[fname]]:
            env[inverse.model_name].invalidate_model([inverse.name], flush=False)

    records = model.browse(ids)
    records.modified(model._fields, create=True)
    records._validate_fields(fnames)
    if cache_name := model._clear_cache_name:
        env.transaction.invalidate_ormcache(cache_name)
    return ids


def convert_xml_import(
        env,
        module,
        xmlfile,
        idref: IdRef | None = None,
        mode: ConvertMode = 'init',
        noupdate=False,
        report=None,
):
    doc = etree.parse(xmlfile)
    schema = os.path.join(config.root_path, 'import_xml.rng')
    relaxng = etree.RelaxNG(etree.parse(schema))
    try:
        relaxng.assert_(doc)
    except Exception:
        _logger.exception("The XML file '%s' does not fit the required schema!", xmlfile.name)
        if jingtrang:
            environ = os.environ.copy()
            environ['JAVA_TOOL_OPTIONS'] = '-Xmx64m -XX:-UseCompressedClassPointers'
            p = subprocess.run(
                ["pyjing", schema, xmlfile.name], stdout=subprocess.PIPE, env=environ,
            )
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
    obj = xml_import(env, module, idref, mode, noupdate=noupdate, xml_filename=xml_filename)
    obj.parse(doc.getroot())
