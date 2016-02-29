# -*- coding: utf-8 -*-
import collections
import copy
import cStringIO
import datetime
import hashlib
import json
import itertools
import logging
import math
import os
import re
import sys
import textwrap
import uuid
from subprocess import Popen, PIPE
from urlparse import urlparse

import babel
import babel.dates
import werkzeug
from lxml import etree, html
from PIL import Image
import psycopg2

import openerp.http
import openerp.tools
from openerp.tools.func import lazy_property
import openerp.tools.lru
from openerp.exceptions import QWebException
from openerp.fields import Datetime
from openerp.http import request
from openerp.tools.safe_eval import safe_eval as eval
from openerp.osv import osv, orm, fields
from openerp.tools import html_escape as escape
from openerp.tools.misc import find_in_path
from openerp.tools.translate import _
from openerp.modules.module import get_resource_path

_logger = logging.getLogger(__name__)

MAX_CSS_RULES = 4095

#--------------------------------------------------------------------
# QWeb template engine
#--------------------------------------------------------------------
class QWebTemplateNotFound(QWebException):
    pass

def raise_qweb_exception(etype=None, **kw):
    if etype is None:
        etype = QWebException
    orig_type, original, tb = sys.exc_info()
    try:
        raise etype, original, tb
    except etype, e:
        for k, v in kw.items():
            e.qweb[k] = v
        # Will use `raise foo from bar` in python 3 and rename cause to __cause__
        e.qweb['cause'] = original
        raise

def _build_attribute(name, value):
    value = escape(value)
    if isinstance(name, unicode): name = name.encode('utf-8')
    if isinstance(value, unicode): value = value.encode('utf-8')
    return ' %s="%s"' % (name, value)

class FileSystemLoader(object):
    def __init__(self, path):
        # TODO: support multiple files #add_file() + add cache
        self.path = path
        self.doc = etree.parse(path).getroot()

    def __iter__(self):
        for node in self.doc:
            name = node.get('t-name')
            if name:
                yield name

    def __call__(self, name):
        for node in self.doc:
            if node.get('t-name') == name:
                root = etree.Element('templates')
                root.append(copy.deepcopy(node))
                arch = etree.tostring(root, encoding='utf-8', xml_declaration=True)
                return arch

class QWebContext(dict):
    def __init__(self, cr, uid, data, loader=None, context=None):
        self.cr = cr
        self.uid = uid
        self.loader = loader
        self.context = context
        dic = dict(data)
        super(QWebContext, self).__init__(dic)
        self['defined'] = lambda key: key in self

    def safe_eval(self, expr):
        locals_dict = collections.defaultdict(lambda: None)
        locals_dict.update(self)
        locals_dict.pop('cr', None)
        locals_dict.pop('loader', None)
        return eval(expr, None, locals_dict, nocopy=True, locals_builtins=True)

    def copy(self):
        """ Clones the current context, conserving all data and metadata
        (loader, template cache, ...)
        """
        return QWebContext(self.cr, self.uid, dict.copy(self),
                           loader=self.loader,
                           context=self.context)

    def __copy__(self):
        return self.copy()

class QWeb(orm.AbstractModel):
    """ Base QWeb rendering engine

    * to customize ``t-field`` rendering, subclass ``ir.qweb.field`` and
      create new models called :samp:`ir.qweb.field.{widget}`
    * alternatively, override :meth:`~.get_converter_for` and return an
      arbitrary model to use as field converter

    Beware that if you need extensions or alterations which could be
    incompatible with other subsystems, you should create a local object
    inheriting from ``ir.qweb`` and customize that.
    """

    _name = 'ir.qweb'

    _void_elements = frozenset([
        u'area', u'base', u'br', u'col', u'embed', u'hr', u'img', u'input',
        u'keygen', u'link', u'menuitem', u'meta', u'param', u'source',
        u'track', u'wbr'])
    _format_regex = re.compile(
        '(?:'
            # ruby-style pattern
            '#\{(.+?)\}'
        ')|(?:'
            # jinja-style pattern
            '\{\{(.+?)\}\}'
        ')')

    def __init__(self, pool, cr):
        super(QWeb, self).__init__(pool, cr)

        self._render_tag = self.prefixed_methods('render_tag_')
        self._render_att = self.prefixed_methods('render_att_')

    def prefixed_methods(self, prefix):
        """ Extracts all methods prefixed by ``prefix``, and returns a mapping
        of (t-name, method) where the t-name is the method name with prefix
        removed and underscore converted to dashes

        :param str prefix:
        :return: dict
        """
        n_prefix = len(prefix)
        return dict(
            (name[n_prefix:].replace('_', '-'), getattr(type(self), name))
            for name in dir(self)
            if name.startswith(prefix)
        )

    def register_tag(self, tag, func):
        self._render_tag[tag] = func

    def get_template(self, name, qwebcontext):
        origin_template = qwebcontext.get('__caller__') or qwebcontext['__stack__'][0]
        try:
            document = qwebcontext.loader(name)
        except ValueError:
            raise_qweb_exception(QWebTemplateNotFound, message="Loader could not find template %r" % name, template=origin_template)

        if hasattr(document, 'documentElement'):
            dom = document
        elif document.startswith("<?xml"):
            dom = etree.fromstring(document)
        else:
            dom = etree.parse(document).getroot()

        res_id = isinstance(name, (int, long)) and name or None
        for node in dom:
            if node.get('t-name') or (res_id and node.tag == "t"):
                return node

        raise QWebTemplateNotFound("Template %r not found" % name, template=origin_template)

    def eval(self, expr, qwebcontext):
        try:
            return qwebcontext.safe_eval(expr)
        except Exception:
            template = qwebcontext.get('__template__')
            raise_qweb_exception(message="Could not evaluate expression %r" % expr, expression=expr, template=template)

    def eval_object(self, expr, qwebcontext):
        return self.eval(expr, qwebcontext)

    def eval_str(self, expr, qwebcontext):
        if expr == "0":
            return qwebcontext.get(0, '')
        val = self.eval(expr, qwebcontext)
        if isinstance(val, unicode):
            return val.encode("utf8")
        if val is False or val is None:
            return ''
        return str(val)

    def eval_format(self, expr, qwebcontext):
        expr, replacements = self._format_regex.subn(
            lambda m: self.eval_str(m.group(1) or m.group(2), qwebcontext),
            expr
        )

        if replacements:
            return expr

        try:
            return str(expr % qwebcontext)
        except Exception:
            template = qwebcontext.get('__template__')
            raise_qweb_exception(message="Format error for expression %r" % expr, expression=expr, template=template)

    def eval_bool(self, expr, qwebcontext):
        return int(bool(self.eval(expr, qwebcontext)))

    def render(self, cr, uid, id_or_xml_id, qwebcontext=None, loader=None, context=None):
        """ render(cr, uid, id_or_xml_id, qwebcontext=None, loader=None, context=None)

        Renders the template specified by the provided template name

        :param qwebcontext: context for rendering the template
        :type qwebcontext: dict or :class:`QWebContext` instance
        :param loader: if ``qwebcontext`` is a dict, loader set into the
                       context instantiated for rendering
        """
        if qwebcontext is None:
            qwebcontext = {}

        if not isinstance(qwebcontext, QWebContext):
            qwebcontext = QWebContext(cr, uid, qwebcontext, loader=loader, context=context)

        qwebcontext['__template__'] = id_or_xml_id
        stack = qwebcontext.get('__stack__', [])
        if stack:
            qwebcontext['__caller__'] = stack[-1]
        stack.append(id_or_xml_id)
        qwebcontext['__stack__'] = stack
        qwebcontext['xmlid'] = str(stack[0]) # Temporary fix

        element = self.get_template(id_or_xml_id, qwebcontext)
        element.attrib.pop("name", False)
        return self.render_node(element, qwebcontext, generated_attributes=qwebcontext.pop('generated_attributes', ''))

    def render_node(self, element, qwebcontext, generated_attributes=''):
        t_render = None
        template_attributes = {}

        debugger = element.get('t-debug')
        if debugger is not None:
            if openerp.tools.config['dev_mode']:
                __import__(debugger).set_trace()  # pdb, ipdb, pudb, ...
            else:
                _logger.warning("@t-debug in template '%s' is only available in --dev mode" % qwebcontext['__template__'])

        for (attribute_name, attribute_value) in element.attrib.iteritems():
            attribute_name = unicode(attribute_name)
            if attribute_name == "groups":
                cr = qwebcontext.get('request') and qwebcontext['request'].cr or None
                uid = qwebcontext.get('request') and qwebcontext['request'].uid or None
                can_see = self.user_has_groups(cr, uid, groups=attribute_value) if cr and uid else False
                if not can_see:
                    return element.tail and self.render_tail(element.tail, element, qwebcontext) or ''

            attribute_value = attribute_value.encode("utf8")

            if attribute_name.startswith("t-"):
                for attribute in self._render_att:
                    if attribute_name[2:].startswith(attribute):
                        attrs = self._render_att[attribute](
                            self, element, attribute_name, attribute_value, qwebcontext)
                        for att, val in attrs:
                            if not val: continue
                            generated_attributes += self.render_attribute(element, att, val, qwebcontext)
                        break
                else:
                    if attribute_name[2:] in self._render_tag:
                        t_render = attribute_name[2:]
                    template_attributes[attribute_name[2:]] = attribute_value
            else:
                generated_attributes += self.render_attribute(element, attribute_name, attribute_value, qwebcontext)

        if t_render:
            result = self._render_tag[t_render](self, element, template_attributes, generated_attributes, qwebcontext)
        else:
            result = self.render_element(element, template_attributes, generated_attributes, qwebcontext)

        if element.tail:
            result += self.render_tail(element.tail, element, qwebcontext)

        if isinstance(result, unicode):
            return result.encode('utf-8')
        return result

    def render_element(self, element, template_attributes, generated_attributes, qwebcontext, inner=None):
        # element: element
        # template_attributes: t-* attributes
        # generated_attributes: generated attributes
        # qwebcontext: values
        # inner: optional innerXml
        name = unicode(element.tag)
        if inner:
            g_inner = inner.encode('utf-8') if isinstance(inner, unicode) else inner
        else:
            g_inner = [] if element.text is None else [self.render_text(element.text, element, qwebcontext)]
            for current_node in element.iterchildren(tag=etree.Element):
                try:
                    g_inner.append(self.render_node(current_node, qwebcontext,
                        generated_attributes= name == "t" and generated_attributes or ''))
                except QWebException:
                    raise
                except Exception:
                    template = qwebcontext.get('__template__')
                    raise_qweb_exception(message="Could not render element %r" % element.tag, node=element, template=template)
        inner = "".join(g_inner)
        trim = template_attributes.get("trim", 0)
        if trim == 0:
            pass
        elif trim == 'left':
            inner = inner.lstrip()
        elif trim == 'right':
            inner = inner.rstrip()
        elif trim == 'both':
            inner = inner.strip()
        if name == "t":
            return inner
        elif len(inner) or name not in self._void_elements:
            return "<%s%s>%s</%s>" % tuple(
                qwebcontext if isinstance(qwebcontext, str) else qwebcontext.encode('utf-8')
                for qwebcontext in (name, generated_attributes, inner, name)
            )
        else:
            return "<%s%s/>" % (name.encode("utf-8"), generated_attributes)

    def render_attribute(self, element, name, value, qwebcontext):
        return _build_attribute(name, value)

    def render_text(self, text, element, qwebcontext):
        return text.encode('utf-8')

    def render_tail(self, tail, element, qwebcontext):
        return tail.encode('utf-8')

    # Attributes
    def render_att_att(self, element, attribute_name, attribute_value, qwebcontext):
        if attribute_name.startswith("t-attf-"):
            return [(attribute_name[7:], self.eval_format(attribute_value, qwebcontext))]

        if attribute_name.startswith("t-att-"):
            return [(attribute_name[6:], self.eval(attribute_value, qwebcontext))]

        result = self.eval_object(attribute_value, qwebcontext)
        if isinstance(result, collections.Mapping):
            return result.iteritems()
        # assume tuple
        return [result]

    # Tags
    def render_tag_raw(self, element, template_attributes, generated_attributes, qwebcontext):
        inner = self.eval_str(template_attributes["raw"], qwebcontext)
        return self.render_element(element, template_attributes, generated_attributes, qwebcontext, inner)

    def render_tag_esc(self, element, template_attributes, generated_attributes, qwebcontext):
        options = json.loads(template_attributes.get('esc-options') or '{}')
        widget = self.get_widget_for(options.get('widget'))
        inner = widget.format(template_attributes['esc'], options, qwebcontext)
        return self.render_element(element, template_attributes, generated_attributes, qwebcontext, inner)

    def _iterate(self, iterable):
        if isinstance (iterable, collections.Mapping):
            return iterable.iteritems()

        return itertools.izip(*itertools.tee(iterable))

    def render_tag_foreach(self, element, template_attributes, generated_attributes, qwebcontext):
        expr = template_attributes["foreach"]
        enum = self.eval_object(expr, qwebcontext)
        if enum is None:
            template = qwebcontext.get('__template__')
            raise QWebException("foreach enumerator %r is not defined while rendering template %r" % (expr, template), template=template)
        if isinstance(enum, int):
            enum = range(enum)

        varname = template_attributes['as'].replace('.', '_')
        copy_qwebcontext = qwebcontext.copy()

        size = None
        if isinstance(enum, collections.Sized):
            size = len(enum)
            copy_qwebcontext["%s_size" % varname] = size

        copy_qwebcontext["%s_all" % varname] = enum
        ru = []
        for index, (item, value) in enumerate(self._iterate(enum)):
            copy_qwebcontext.update({
                varname: item,
                '%s_value' % varname: value,
                '%s_index' % varname: index,
                '%s_first' % varname: index == 0,
            })
            if size is not None:
                copy_qwebcontext['%s_last' % varname] = index + 1 == size
            if index % 2:
                copy_qwebcontext.update({
                    '%s_parity' % varname: 'odd',
                    '%s_even' % varname: False,
                    '%s_odd' % varname: True,
                })
            else:
                copy_qwebcontext.update({
                    '%s_parity' % varname: 'even',
                    '%s_even' % varname: True,
                    '%s_odd' % varname: False,
                })
            ru.append(self.render_element(element, template_attributes, generated_attributes, copy_qwebcontext))

        for k in qwebcontext.keys():
            qwebcontext[k] = copy_qwebcontext[k]

        return "".join(ru)

    def render_tag_if(self, element, template_attributes, generated_attributes, qwebcontext):
        if self.eval_bool(template_attributes["if"], qwebcontext):
            return self.render_element(element, template_attributes, generated_attributes, qwebcontext)
        return ""

    def render_tag_call(self, element, template_attributes, generated_attributes, qwebcontext):
        d = qwebcontext.copy()

        if 'lang' in template_attributes:
            init_lang = d.context.get('lang', 'en_US')
            lang = template_attributes['lang']
            d.context['lang'] = self.eval(lang, d) or lang
            if not self.pool['res.lang'].search(d.cr, d.uid, [('code', '=', lang)], count=True, context=d.context):
                _logger.info("'%s' is not a valid language code, is an empty field or is not installed, falling back to en_US", lang)

        d[0] = self.render_element(element, template_attributes, generated_attributes, d)
        cr = d.get('request') and d['request'].cr or None
        uid = d.get('request') and d['request'].uid or None

        template = self.eval_format(template_attributes["call"], d)
        try:
            template = int(template)
        except ValueError:
            pass

        d['generated_attributes'] = generated_attributes
        res = self.render(cr, uid, template, d)

        # we need to reset the lang after the rendering
        if 'lang' in template_attributes:
            d.context['lang'] = init_lang

        return res

    def render_tag_call_assets(self, element, template_attributes, generated_attributes, qwebcontext):
        """ This special 't-call' tag can be used in order to aggregate/minify javascript and css assets"""
        if len(element):
            # An asset bundle is rendered in two differents contexts (when genereting html and
            # when generating the bundle itself) so they must be qwebcontext free
            # even '0' variable is forbidden
            template = qwebcontext.get('__template__')
            raise QWebException("t-call-assets cannot contain children nodes", template=template)
        xmlid = template_attributes['call-assets']
        cr, uid, context = [getattr(qwebcontext, attr) for attr in ('cr', 'uid', 'context')]
        bundle = AssetsBundle(xmlid, cr=cr, uid=uid, context=context, registry=self.pool)
        css = self.get_attr_bool(template_attributes.get('css'), default=True)
        js = self.get_attr_bool(template_attributes.get('js'), default=True)
        async = self.get_attr_bool(template_attributes.get('async'), default=False)
        return bundle.to_html(css=css, js=js, debug=bool(qwebcontext.get('debug')), async=async, qwebcontext=qwebcontext)

    def render_tag_set(self, element, template_attributes, generated_attributes, qwebcontext):
        if "value" in template_attributes:
            qwebcontext[template_attributes["set"]] = self.eval_object(template_attributes["value"], qwebcontext)
        elif "valuef" in template_attributes:
            qwebcontext[template_attributes["set"]] = self.eval_format(template_attributes["valuef"], qwebcontext)
        else:
            qwebcontext[template_attributes["set"]] = self.render_element(element, template_attributes, generated_attributes, qwebcontext)
        return ""

    def render_tag_field(self, element, template_attributes, generated_attributes, qwebcontext):
        """ eg: <span t-record="browse_record(res.partner, 1)" t-field="phone">+1 555 555 8069</span>"""
        node_name = element.tag
        assert node_name not in ("table", "tbody", "thead", "tfoot", "tr", "td",
                                 "li", "ul", "ol", "dl", "dt", "dd"),\
            "RTE widgets do not work correctly on %r elements" % node_name
        assert node_name != 't',\
            "t-field can not be used on a t element, provide an actual HTML node"

        record, field_name = template_attributes["field"].rsplit('.', 1)
        record = self.eval_object(record, qwebcontext)
        field = record._fields[field_name]
        foptions = self.eval_format(template_attributes.get('field-options') or '{}', qwebcontext)
        options = json.loads(foptions)

        field_type = get_field_type(field, options)

        converter = self.get_converter_for(field_type)

        return converter.to_html(qwebcontext.cr, qwebcontext.uid, field_name, record, options,
                                 element, template_attributes, generated_attributes, qwebcontext, context=qwebcontext.context)

    def get_converter_for(self, field_type):
        """ returns a :class:`~openerp.models.Model` used to render a
        ``t-field``.

        By default, tries to get the model named
        :samp:`ir.qweb.field.{field_type}`, falling back on ``ir.qweb.field``.

        :param str field_type: type or widget of field to render
        """
        return self.pool.get('ir.qweb.field.' + field_type, self.pool['ir.qweb.field'])

    def get_widget_for(self, widget):
        """ returns a :class:`~openerp.models.Model` used to render a
        ``t-esc``

        :param str widget: name of the widget to use, or ``None``
        """
        widget_model = ('ir.qweb.widget.' + widget) if widget else 'ir.qweb.widget'
        return self.pool.get(widget_model) or self.pool['ir.qweb.widget']

    def get_attr_bool(self, attr, default=False):
        if attr:
            attr = attr.lower()
            if attr in ('false', '0'):
                return False
            elif attr in ('true', '1'):
                return True
        return default

#--------------------------------------------------------------------
# QWeb Fields converters
#--------------------------------------------------------------------

class FieldConverter(osv.AbstractModel):
    """ Used to convert a t-field specification into an output HTML field.

    :meth:`~.to_html` is the entry point of this conversion from QWeb, it:

    * converts the record value to html using :meth:`~.record_to_html`
    * generates the metadata attributes (``data-oe-``) to set on the root
      result node
    * generates the root result node itself through :meth:`~.render_element`
    """
    _name = 'ir.qweb.field'

    def attributes(self, cr, uid, field_name, record, options,
                   source_element, g_att, t_att, qweb_context,
                   context=None):
        """ attributes(cr, uid, field_name, record, options, source_element, g_att, t_att, qweb_context, context=None)

        Generates the metadata attributes (prefixed by ``data-oe-`` for the
        root node of the field conversion. Attribute values are escaped by the
        parent.

        The default attributes are:

        * ``model``, the name of the record's model
        * ``id`` the id of the record to which the field belongs
        * ``field`` the name of the converted field
        * ``type`` the logical field type (widget, may not match the field's
          ``type``, may not be any Field subclass name)
        * ``translate``, a boolean flag (``0`` or ``1``) denoting whether the
          field is translatable
        * ``readonly``, has this attribute if the field is readonly
        * ``expression``, the original expression

        :returns: iterable of (attribute name, attribute value) pairs.
        """
        field = record._fields[field_name]
        field_type = get_field_type(field, options)
        data = [
            ('data-oe-model', record._name),
            ('data-oe-id', record.id),
            ('data-oe-field', field_name),
            ('data-oe-type', field_type),
            ('data-oe-expression', t_att['field']),
        ]
        if field.readonly:
            data.append(('data-oe-readonly', 1))
        return data

    def value_to_html(self, cr, uid, value, field, options=None, context=None):
        """ value_to_html(cr, uid, value, field, options=None, context=None)

        Converts a single value to its HTML version/output
        """
        if not value: return ''
        return value

    def record_to_html(self, cr, uid, field_name, record, options=None, context=None):
        """ record_to_html(cr, uid, field_name, record, options=None, context=None)

        Converts the specified field of the browse_record ``record`` to HTML
        """
        field = record._fields[field_name]
        return self.value_to_html(
            cr, uid, record[field_name], field, options=options, context=context)

    def to_html(self, cr, uid, field_name, record, options,
                source_element, t_att, g_att, qweb_context, context=None):
        """ to_html(cr, uid, field_name, record, options, source_element, t_att, g_att, qweb_context, context=None)

        Converts a ``t-field`` to its HTML output. A ``t-field`` may be
        extended by a ``t-field-options``, which is a JSON-serialized mapping
        of configuration values.

        A default configuration key is ``widget`` which can override the
        field's own ``_type``.
        """
        try:
            content = self.record_to_html(cr, uid, field_name, record, options, context=context)
            if options.get('html-escape', True):
                content = escape(content)
            elif hasattr(content, '__html__'):
                content = content.__html__()
        except Exception:
            _logger.warning("Could not get field %s for model %s",
                            field_name, record._name, exc_info=True)
            content = None

        inherit_branding = context and context.get('inherit_branding')
        if not inherit_branding and context and context.get('inherit_branding_auto'):
            inherit_branding = self.pool['ir.model.access'].check(cr, uid, record._name, 'write', False, context=context)
        translate = context and context.get('edit_translations') and context.get('translatable') and getattr(record._fields[field_name], 'translate', False)

        if inherit_branding or translate:
            # add branding attributes
            g_att += ''.join(
                _build_attribute(name, value)
                for name, value in self.attributes(
                    cr, uid, field_name, record, options,
                    source_element, g_att, t_att, qweb_context,
                    context=context)
            )

        return self.render_element(cr, uid, source_element, t_att, g_att,
                                   qweb_context, content)

    def qweb_object(self):
        return self.pool['ir.qweb']

    def render_element(self, cr, uid, source_element, t_att, g_att,
                       qweb_context, content):
        """ render_element(cr, uid, source_element, t_att, g_att, qweb_context, content)

        Final rendering hook, by default just calls ir.qweb's ``render_element``
        """
        return self.qweb_object().render_element(
            source_element, t_att, g_att, qweb_context, content or '')

    def user_lang(self, cr, uid, context):
        """ user_lang(cr, uid, context)

        Fetches the res.lang object corresponding to the language code stored
        in the user's context. Fallbacks to en_US if no lang is present in the
        context *or the language code is not valid*.

        :returns: res.lang browse_record
        """
        if context is None: context = {}

        lang_code = context.get('lang') or 'en_US'
        Lang = self.pool['res.lang']

        return Lang.browse(cr, uid, Lang._lang_get(cr, uid, lang_code), context=context)

class IntegerConverter(osv.AbstractModel):
    _name = 'ir.qweb.field.integer'
    _inherit = 'ir.qweb.field'

    def value_to_html(self, cr, uid, value, field, options=None, context=None):
        if context is None:
            context = {}

        lang_code = context.get('lang') or 'en_US'
        return self.pool['res.lang'].format(cr, uid, [lang_code], '%d', value, grouping=True)

class FloatConverter(osv.AbstractModel):
    _name = 'ir.qweb.field.float'
    _inherit = 'ir.qweb.field'

    def precision(self, cr, uid, field, options=None, context=None):
        _, precision = field.digits or (None, None)
        return precision

    def value_to_html(self, cr, uid, value, field, options=None, context=None):
        if context is None:
            context = {}
        precision = self.precision(cr, uid, field, options=options, context=context)
        fmt = '%f' if precision is None else '%.{precision}f'

        lang_code = context.get('lang') or 'en_US'
        lang = self.pool['res.lang']
        formatted = lang.format(cr, uid, [lang_code], fmt.format(precision=precision), value, grouping=True)

        # %f does not strip trailing zeroes. %g does but its precision causes
        # it to switch to scientific notation starting at a million *and* to
        # strip decimals. So use %f and if no precision was specified manually
        # strip trailing 0.
        if precision is None:
            formatted = re.sub(r'(?:(0|\d+?)0+)$', r'\1', formatted)
        return formatted

class DateConverter(osv.AbstractModel):
    _name = 'ir.qweb.field.date'
    _inherit = 'ir.qweb.field'

    def value_to_html(self, cr, uid, value, field, options=None, context=None):
        if not value or len(value)<10: return ''
        lang = self.user_lang(cr, uid, context=context)
        locale = babel.Locale.parse(lang.code)

        if isinstance(value, basestring):
            value = datetime.datetime.strptime(
                value[:10], openerp.tools.DEFAULT_SERVER_DATE_FORMAT)

        if options and 'format' in options:
            pattern = options['format']
        else:
            strftime_pattern = lang.date_format
            pattern = openerp.tools.posix_to_ldml(strftime_pattern, locale=locale)

        return babel.dates.format_date(
            value, format=pattern,
            locale=locale)

class DateTimeConverter(osv.AbstractModel):
    _name = 'ir.qweb.field.datetime'
    _inherit = 'ir.qweb.field'

    def value_to_html(self, cr, uid, value, field, options=None, context=None):
        if not value: return ''
        lang = self.user_lang(cr, uid, context=context)
        locale = babel.Locale.parse(lang.code)

        if isinstance(value, basestring):
            value = datetime.datetime.strptime(
                value, openerp.tools.DEFAULT_SERVER_DATETIME_FORMAT)
        value = fields.datetime.context_timestamp(
            cr, uid, timestamp=value, context=context)

        if options and 'format' in options:
            pattern = options['format']
        else:
            strftime_pattern = (u"%s %s" % (lang.date_format, lang.time_format))
            pattern = openerp.tools.posix_to_ldml(strftime_pattern, locale=locale)

        if options and options.get('hide_seconds'):
            pattern = pattern.replace(":ss", "").replace(":s", "")

        return babel.dates.format_datetime(value, format=pattern, locale=locale)

class TextConverter(osv.AbstractModel):
    _name = 'ir.qweb.field.text'
    _inherit = 'ir.qweb.field'

    def value_to_html(self, cr, uid, value, field, options=None, context=None):
        """
        Escapes the value and converts newlines to br. This is bullshit.
        """
        if not value: return ''

        return nl2br(value, options=options)

class SelectionConverter(osv.AbstractModel):
    _name = 'ir.qweb.field.selection'
    _inherit = 'ir.qweb.field'

    def record_to_html(self, cr, uid, field_name, record, options=None, context=None):
        value = record[field_name]
        if not value: return ''
        field = record._fields[field_name]
        selection = dict(field.get_description(record.env)['selection'])
        return self.value_to_html(
            cr, uid, selection[value], field, options=options)

class ManyToOneConverter(osv.AbstractModel):
    _name = 'ir.qweb.field.many2one'
    _inherit = 'ir.qweb.field'

    def record_to_html(self, cr, uid, field_name, record, options=None, context=None):
        [read] = record.read([field_name])
        if not read[field_name]: return ''
        _, value = read[field_name]
        return nl2br(value, options=options)

class HTMLConverter(osv.AbstractModel):
    _name = 'ir.qweb.field.html'
    _inherit = 'ir.qweb.field'

    def value_to_html(self, cr, uid, value, field, options=None, context=None):
        return HTMLSafe(value or '')

class ImageConverter(osv.AbstractModel):
    """ ``image`` widget rendering, inserts a data:uri-using image tag in the
    document. May be overridden by e.g. the website module to generate links
    instead.

    .. todo:: what happens if different output need different converters? e.g.
              reports may need embedded images or FS links whereas website
              needs website-aware
    """
    _name = 'ir.qweb.field.image'
    _inherit = 'ir.qweb.field'

    def value_to_html(self, cr, uid, value, field, options=None, context=None):
        try:
            image = Image.open(cStringIO.StringIO(value.decode('base64')))
            image.verify()
        except IOError:
            raise ValueError("Non-image binary fields can not be converted to HTML")
        except: # image.verify() throws "suitable exceptions", I have no idea what they are
            raise ValueError("Invalid image content")

        return HTMLSafe('<img src="data:%s;base64,%s">' % (Image.MIME[image.format], value))

class MonetaryConverter(osv.AbstractModel):
    """ ``monetary`` converter, has a mandatory option
    ``display_currency`` only if field is not of type Monetary.
    Otherwise, if we are in presence of a monetary field, the field definition must
    have a currency_field attribute set.

    The currency is used for formatting *and rounding* of the float value. It
    is assumed that the linked res_currency has a non-empty rounding value and
    res.currency's ``round`` method is used to perform rounding.

    .. note:: the monetary converter internally adds the qweb context to its
              options mapping, so that the context is available to callees.
              It's set under the ``_qweb_context`` key.
    """
    _name = 'ir.qweb.field.monetary'
    _inherit = 'ir.qweb.field'

    def to_html(self, cr, uid, field_name, record, options,
                source_element, t_att, g_att, qweb_context, context=None):
        options['_qweb_context'] = qweb_context
        return super(MonetaryConverter, self).to_html(
            cr, uid, field_name, record, options,
            source_element, t_att, g_att, qweb_context, context=context)

    def record_to_html(self, cr, uid, field_name, record, options, context=None):
        if context is None:
            context = {}
        Currency = self.pool['res.currency']
        cur_field = record._fields[field_name]
        display_currency = False
        #currency should be specified by monetary field
        if cur_field.type == 'monetary' and cur_field.currency_field:
            display_currency = record[cur_field.currency_field]
        #otherwise fall back to old method
        if not display_currency:
            display_currency = self.display_currency(cr, uid, options['display_currency'], options)

        # lang.format mandates a sprintf-style format. These formats are non-
        # minimal (they have a default fixed precision instead), and
        # lang.format will not set one by default. currency.round will not
        # provide one either. So we need to generate a precision value
        # (integer > 0) from the currency's rounding (a float generally < 1.0).
        fmt = "%.{0}f".format(display_currency.decimal_places)

        from_amount = record[field_name]

        if options.get('from_currency'):
            from_currency = self.display_currency(cr, uid, options['from_currency'], options)
            from_amount = Currency.compute(cr, uid, from_currency.id, display_currency.id, from_amount)

        lang_code = context.get('lang') or 'en_US'
        lang = self.pool['res.lang']
        formatted_amount = lang.format(cr, uid, [lang_code],
            fmt, Currency.round(cr, uid, display_currency, from_amount),
            grouping=True, monetary=True)

        pre = post = u''
        if display_currency.position == 'before':
            pre = u'{symbol}\N{NO-BREAK SPACE}'
        else:
            post = u'\N{NO-BREAK SPACE}{symbol}'

        return HTMLSafe(u'{pre}<span class="oe_currency_value">{0}</span>{post}'.format(
            formatted_amount,
            pre=pre, post=post,
        ).format(
            symbol=display_currency.symbol,
        ))

    def display_currency(self, cr, uid, currency, options):
        return self.qweb_object().eval_object(
            currency, options['_qweb_context'])

TIMEDELTA_UNITS = (
    ('year',   3600 * 24 * 365),
    ('month',  3600 * 24 * 30),
    ('week',   3600 * 24 * 7),
    ('day',    3600 * 24),
    ('hour',   3600),
    ('minute', 60),
    ('second', 1)
)
class DurationConverter(osv.AbstractModel):
    """ ``duration`` converter, to display integral or fractional values as
    human-readable time spans (e.g. 1.5 as "1 hour 30 minutes").

    Can be used on any numerical field.

    Has a mandatory option ``unit`` which can be one of ``second``, ``minute``,
    ``hour``, ``day``, ``week`` or ``year``, used to interpret the numerical
    field value before converting it.

    Sub-second values will be ignored.
    """
    _name = 'ir.qweb.field.duration'
    _inherit = 'ir.qweb.field'

    def value_to_html(self, cr, uid, value, field, options=None, context=None):
        units = dict(TIMEDELTA_UNITS)
        if value < 0:
            raise ValueError(_("Durations can't be negative"))
        if not options or options.get('unit') not in units:
            raise ValueError(_("A unit must be provided to duration widgets"))

        locale = babel.Locale.parse(
            self.user_lang(cr, uid, context=context).code)
        factor = units[options['unit']]

        sections = []
        r = value * factor
        for unit, secs_per_unit in TIMEDELTA_UNITS:
            v, r = divmod(r, secs_per_unit)
            if not v: continue
            section = babel.dates.format_timedelta(
                v*secs_per_unit, threshold=1, locale=locale)
            if section:
                sections.append(section)
        return ' '.join(sections)


class RelativeDatetimeConverter(osv.AbstractModel):
    _name = 'ir.qweb.field.relative'
    _inherit = 'ir.qweb.field'

    def value_to_html(self, cr, uid, value, field, options=None, context=None):
        parse_format = openerp.tools.DEFAULT_SERVER_DATETIME_FORMAT
        locale = babel.Locale.parse(
            self.user_lang(cr, uid, context=context).code)

        if isinstance(value, basestring):
            value = datetime.datetime.strptime(value, parse_format)

        # value should be a naive datetime in UTC. So is fields.Datetime.now()
        reference = datetime.datetime.strptime(field.now(), parse_format)

        return babel.dates.format_timedelta(
            value - reference, add_direction=True, locale=locale)

class Contact(orm.AbstractModel):
    _name = 'ir.qweb.field.contact'
    _inherit = 'ir.qweb.field.many2one'

    def record_to_html(self, cr, uid, field_name, record, options=None, context=None):
        if context is None:
            context = {}

        if options is None:
            options = {}
        opf = options.get('fields') or ["name", "address", "phone", "mobile", "fax", "email"]

        value_rec = record[field_name]
        if not value_rec:
            return None
        value_rec = value_rec.sudo().with_context(show_address=True)
        value = value_rec.name_get()[0][1]

        val = {
            'name': value.split("\n")[0],
            'address': escape("\n".join(value.split("\n")[1:])).strip(),
            'phone': value_rec.phone,
            'mobile': value_rec.mobile,
            'fax': value_rec.fax,
            'city': value_rec.city,
            'country_id': value_rec.country_id.display_name,
            'website': value_rec.website,
            'email': value_rec.email,
            'fields': opf,
            'object': value_rec,
            'options': options
        }

        html = self.pool["ir.ui.view"].render(cr, uid, "base.contact", val, engine='ir.qweb', context=context).decode('utf8')

        return HTMLSafe(html)

class QwebView(orm.AbstractModel):
    _name = 'ir.qweb.field.qweb'
    _inherit = 'ir.qweb.field.many2one'

    def record_to_html(self, cr, uid, field_name, record, options=None, context=None):
        if not getattr(record, field_name):
            return None

        view = getattr(record, field_name)

        if view._model._name != "ir.ui.view":
            _logger.warning("%s.%s must be a 'ir.ui.view' model." % (record, field_name))
            return None

        ctx = (context or {}).copy()
        ctx['object'] = record
        html = view.render(ctx, engine='ir.qweb', context=ctx).decode('utf8')

        return HTMLSafe(html)

class QwebWidget(osv.AbstractModel):
    _name = 'ir.qweb.widget'

    def _format(self, inner, options, qwebcontext):
        return self.pool['ir.qweb'].eval_str(inner, qwebcontext)

    def format(self, inner, options, qwebcontext):
        return escape(self._format(inner, options, qwebcontext))

class QwebWidgetMonetary(osv.AbstractModel):
    _name = 'ir.qweb.widget.monetary'
    _inherit = 'ir.qweb.widget'

    def _format(self, inner, options, qwebcontext):
        inner = self.pool['ir.qweb'].eval(inner, qwebcontext)
        display = self.pool['ir.qweb'].eval_object(options['display_currency'], qwebcontext)
        precision = int(round(math.log10(display.rounding)))
        fmt = "%.{0}f".format(-precision if precision < 0 else 0)
        lang_code = qwebcontext.context.get('lang') or 'en_US'
        formatted_amount = self.pool['res.lang'].format(
            qwebcontext.cr, qwebcontext.uid, [lang_code], fmt, inner, grouping=True, monetary=True
        )
        pre = post = u''
        if display.position == 'before':
            pre = u'{symbol}\N{NO-BREAK SPACE}'
        else:
            post = u'\N{NO-BREAK SPACE}{symbol}'

        return u'{pre}{0}{post}'.format(
            formatted_amount, pre=pre, post=post
        ).format(symbol=display.symbol,)

class HTMLSafe(object):
    """ HTMLSafe string wrapper, Werkzeug's escape() has special handling for
    objects with a ``__html__`` methods but AFAIK does not provide any such
    object.

    Wrapping a string in HTML will prevent its escaping
    """
    __slots__ = ['string']
    def __init__(self, string):
        self.string = string
    def __html__(self):
        return self.string
    def __str__(self):
        s = self.string
        if isinstance(s, unicode):
            return s.encode('utf-8')
        return s
    def __unicode__(self):
        s = self.string
        if isinstance(s, str):
            return s.decode('utf-8')
        return s

def nl2br(string, options=None):
    """ Converts newlines to HTML linebreaks in ``string``. Automatically
    escapes content unless options['html-escape'] is set to False, and returns
    the result wrapped in an HTMLSafe object.

    :param str string:
    :param dict options:
    :rtype: HTMLSafe
    """
    if options is None: options = {}

    if options.get('html-escape', True):
        string = escape(string)
    return HTMLSafe(string.replace('\n', '<br>\n'))

def get_field_type(field, options):
    """ Gets a t-field's effective type from the field definition and its options """
    return options.get('widget', field.type)

class AssetError(Exception):
    pass
class AssetNotFound(AssetError):
    pass

class AssetsBundle(object):
    rx_css_import = re.compile("(@import[^;{]+;?)", re.M)
    rx_preprocess_imports = re.compile("""(@import\s?['"]([^'"]+)['"](;?))""")
    rx_css_split = re.compile("\/\*\! ([a-f0-9-]+) \*\/")

    def __init__(self, xmlid, cr=None, uid=None, context=None, registry=None, max_css_rules=MAX_CSS_RULES):
        self.xmlid = xmlid
        self.cr = request.cr if cr is None else cr
        self.uid = request.uid if uid is None else uid
        self.context = request.context if context is None else context
        self.registry = request.registry if registry is None else registry
        self.max_css_rules = max_css_rules
        self.javascripts = []
        self.stylesheets = []
        self.css_errors = []
        self.remains = []
        self._checksum = None

        context = self.context.copy()
        context['inherit_branding'] = False
        context['inherit_branding_auto'] = False
        context['rendering_bundle'] = True
        self.html = self.registry['ir.ui.view'].render(self.cr, self.uid, xmlid, context=context)
        self.parse()

    def parse(self):
        fragments = html.fragments_fromstring(self.html)
        for el in fragments:
            if isinstance(el, basestring):
                self.remains.append(el)
            elif isinstance(el, html.HtmlElement):
                src = el.get('src', '')
                href = el.get('href', '')
                atype = el.get('type')
                media = el.get('media')
                if el.tag == 'style':
                    if atype == 'text/sass' or src.endswith('.sass'):
                        self.stylesheets.append(SassStylesheetAsset(self, inline=el.text, media=media))
                    elif atype == 'text/less' or src.endswith('.less'):
                        self.stylesheets.append(LessStylesheetAsset(self, inline=el.text, media=media))
                    else:
                        self.stylesheets.append(StylesheetAsset(self, inline=el.text, media=media))
                elif el.tag == 'link' and el.get('rel') == 'stylesheet' and self.can_aggregate(href):
                    if href.endswith('.sass') or atype == 'text/sass':
                        self.stylesheets.append(SassStylesheetAsset(self, url=href, media=media))
                    elif href.endswith('.less') or atype == 'text/less':
                        self.stylesheets.append(LessStylesheetAsset(self, url=href, media=media))
                    else:
                        self.stylesheets.append(StylesheetAsset(self, url=href, media=media))
                elif el.tag == 'script' and not src:
                    self.javascripts.append(JavascriptAsset(self, inline=el.text))
                elif el.tag == 'script' and self.can_aggregate(src):
                    self.javascripts.append(JavascriptAsset(self, url=src))
                else:
                    self.remains.append(html.tostring(el))
            else:
                try:
                    self.remains.append(html.tostring(el))
                except Exception:
                    # notYETimplementederror
                    raise NotImplementedError

    def can_aggregate(self, url):
        return not urlparse(url).netloc and not url.startswith('/web/content')

    def to_html(self, sep=None, css=True, js=True, debug=False, async=False, qwebcontext=None):
        if sep is None:
            sep = '\n            '
        response = []
        if debug:
            if css and self.stylesheets:
                if not self.is_css_preprocessed():
                    self.preprocess_css(debug=debug)
                    if self.css_errors:
                        msg = '\n'.join(self.css_errors)
                        self.stylesheets.append(StylesheetAsset(self, inline=self.css_message(msg)))
                for style in self.stylesheets:
                    response.append(style.to_html())
            if js:
                for jscript in self.javascripts:
                    response.append(jscript.to_html())
        else:
            if qwebcontext is None:
                qwebcontext = QWebContext(self.cr, self.uid, {})
            if css and self.stylesheets:
                css_attachments = self.css()
                if not self.css_errors:
                    for attachment in css_attachments:
                        el = etree.fromstring('<link href="%s" rel="stylesheet"/>' % attachment.url)
                        response.append(self.registry['ir.qweb'].render_node(el, qwebcontext))
                else:
                    msg = '\n'.join(self.css_errors)
                    self.stylesheets.append(StylesheetAsset(self, inline=self.css_message(msg)))
                    for style in self.stylesheets:
                        response.append(style.to_html())
            if js and self.javascripts:
                el = etree.fromstring('<script %s type="text/javascript" src="%s"></script>' % (async and 'async="async"' or '', self.js().url))
                response.append(self.registry['ir.qweb'].render_node(el, qwebcontext))
        response.extend(self.remains)
        return sep + sep.join(response)

    @lazy_property
    def last_modified(self):
        """Returns last modified date of linked files"""
        return max(itertools.chain(
            (asset.last_modified for asset in self.javascripts),
            (asset.last_modified for asset in self.stylesheets),
        ))

    @lazy_property
    def version(self):
        return self.checksum[0:7]

    @lazy_property
    def checksum(self):
        """
        Not really a full checksum.
        We compute a SHA1 on the rendered bundle + max linked files last_modified date
        """
        check = self.html + str(self.last_modified)
        return hashlib.sha1(check).hexdigest()

    def clean_attachments(self, type):
        """ Takes care of deleting any outdated ir.attachment records associated to a bundle before
        saving a fresh one.

        When `type` is css we need to check that we are deleting a different version (and not *any*
        version) because css may be paginated and, therefore, may produce multiple attachments for
        the same bundle's version.

        When `type` is js we need to check that we are deleting a different version (and not *any*
        version) because, as one of the creates in `save_attachment` can trigger a rollback, the
        call to `clean_attachments ` is made at the end of the method in order to avoid the rollback
        of an ir.attachment unlink (because we cannot rollback a removal on the filestore), thus we
        must exclude the current bundle.
        """
        ira = self.registry['ir.attachment']
        domain = [
            ('url', '=like', '/web/content/%-%/{0}%.{1}'.format(self.xmlid, type)),  # The wilcards are id, version and pagination number (if any)
            '!', ('url', '=like', '/web/content/%-{}/%'.format(self.version))
        ]
        attachment_ids = ira.search(self.cr, openerp.SUPERUSER_ID, domain, context=self.context)
        return ira.unlink(self.cr, openerp.SUPERUSER_ID, attachment_ids, context=self.context)

    def get_attachments(self, type, inc=None):
        ira = self.registry['ir.attachment']
        domain = [('url', '=like', '/web/content/%%-%s/%s%s.%s' % (self.version, self.xmlid, ('%%' if inc is None else '.%s' % inc), type))]
        attachment_ids = ira.search(self.cr, openerp.SUPERUSER_ID, domain, order='name asc', context=self.context)
        return ira.browse(self.cr, openerp.SUPERUSER_ID, attachment_ids, context=self.context)

    def save_attachment(self, type, content, inc=None):
        ira = self.registry['ir.attachment']

        fname = '%s%s.%s' % (self.xmlid, ('' if inc is None else '.%s' % inc), type)
        values = {
            'name': "/web/content/%s" % type,
            'datas_fname': fname,
            'res_model': 'ir.ui.view',
            'res_id': False,
            'type': 'binary',
            'public': True,
            'datas': content.encode('utf8').encode('base64'),
        }
        attachment_id = ira.create(self.cr, openerp.SUPERUSER_ID, values, context=self.context)

        url = '/web/content/%s-%s/%s' % (attachment_id, self.version, fname)
        values = {
            'name': url,
            'url': url,
        }
        ira.write(self.cr, openerp.SUPERUSER_ID, attachment_id, values, context=self.context)

        if self.context.get('commit_assetsbundle') is True:
            self.cr.commit()

        self.clean_attachments(type)

        return ira.browse(self.cr, openerp.SUPERUSER_ID, attachment_id, context=self.context)

    def js(self):
        attachments = self.get_attachments('js')
        if not attachments:
            content = ';\n'.join(asset.minify() for asset in self.javascripts)
            return self.save_attachment('js', content)
        return attachments[0]

    def css(self):
        attachments = self.get_attachments('css')
        if not attachments:
            # get css content
            css = self.preprocess_css()
            if self.css_errors:
                return

            # move up all @import rules to the top
            matches = []
            css = re.sub(self.rx_css_import, lambda matchobj: matches.append(matchobj.group(0)) and '', css)
            matches.append(css)
            css = u'\n'.join(matches)

            # split for browser max file size and browser max expression
            re_rules = '([^{]+\{(?:[^{}]|\{[^{}]*\})*\})'
            re_selectors = '()(?:\s*@media\s*[^{]*\{)?(?:\s*(?:[^,{]*(?:,|\{(?:[^}]*\}))))'
            page = []
            pages = [page]
            page_selectors = 0
            for rule in re.findall(re_rules, css):
                selectors = len(re.findall(re_selectors, rule))
                if page_selectors + selectors <= self.max_css_rules:
                    page_selectors += selectors
                    page.append(rule)
                else:
                    pages.append([rule])
                    page = pages[-1]
                    page_selectors = selectors
            for idx, page in enumerate(pages):
                self.save_attachment("css", ' '.join(page), inc=idx)
            attachments = self.get_attachments('css')
        return attachments

    def css_message(self, message):
        # '\A' == css content carriage return
        message = message.replace('\n', '\\A ').replace('"', '\\"')
        return """
            body:before {
                background: #ffc;
                width: 100%%;
                font-size: 14px;
                font-family: monospace;
                white-space: pre;
                content: "%s";
            }
        """ % message

    def is_css_preprocessed(self):
        uid = openerp.SUPERUSER_ID
        preprocessed = True
        for atype in (SassStylesheetAsset, LessStylesheetAsset):
            outdated = False
            assets = dict((asset.html_url, asset) for asset in self.stylesheets if isinstance(asset, atype))
            if assets:
                assets_domain = [('url', 'in', assets.keys())]
                ira_ids = self.registry['ir.attachment'].search(self.cr, uid, assets_domain)
                ira_records = self.registry['ir.attachment'].browse(self.cr, uid, ira_ids)
                for ira_record in ira_records:
                    asset = assets[ira_record.url]
                    if asset.last_modified > Datetime.from_string(ira_record['__last_update']):
                        outdated = True
                        break
                    if asset._content is None:
                        asset._content = ira_record.datas and ira_record.datas.decode('base64').decode('utf8') or ''
                        if not asset._content and ira_record.file_size > 0:
                            asset._content = None # file missing, force recompile

                if any(asset._content is None for asset in assets.itervalues()):
                    outdated = True

                if outdated:
                    if ira_ids:
                        self.registry['ir.attachment'].unlink(self.cr, uid, ira_ids)
                    preprocessed = False

        return preprocessed

    def preprocess_css(self, debug=False):
        """
            Checks if the bundle contains any sass/less content, then compiles it to css.
            Returns the bundle's flat css.
        """
        for atype in (SassStylesheetAsset, LessStylesheetAsset):
            assets = [asset for asset in self.stylesheets if isinstance(asset, atype)]
            if assets:
                cmd = assets[0].get_command()
                source = '\n'.join([asset.get_source() for asset in assets])
                compiled = self.compile_css(cmd, source)

                fragments = self.rx_css_split.split(compiled)
                at_rules = fragments.pop(0)
                if at_rules:
                    # Sass and less moves @at-rules to the top in order to stay css 2.1 compatible
                    self.stylesheets.insert(0, StylesheetAsset(self, inline=at_rules))
                while fragments:
                    asset_id = fragments.pop(0)
                    asset = next(asset for asset in self.stylesheets if asset.id == asset_id)
                    asset._content = fragments.pop(0)

                    if debug:
                        try:
                            ira = self.registry['ir.attachment']
                            fname = os.path.basename(asset.url)
                            url = asset.html_url
                            with self.cr.savepoint():
                                ira.create(self.cr, openerp.SUPERUSER_ID, dict(
                                    datas=asset.content.encode('utf8').encode('base64'),
                                    mimetype='text/css',
                                    type='binary',
                                    name=url,
                                    url=url,
                                    datas_fname=fname,
                                    res_model=False,
                                    res_id=False,
                                ), context=self.context)

                            if self.context.get('commit_assetsbundle') is True:
                                self.cr.commit()
                        except psycopg2.Error:
                            pass

        return '\n'.join(asset.minify() for asset in self.stylesheets)

    def compile_css(self, cmd, source):
        """Sanitizes @import rules, remove duplicates @import rules, then compile"""
        imports = []
        def sanitize(matchobj):
            ref = matchobj.group(2)
            line = '@import "%s"%s' % (ref, matchobj.group(3))
            if '.' not in ref and line not in imports and not ref.startswith(('.', '/', '~')):
                imports.append(line)
                return line
            msg = "Local import '%s' is forbidden for security reasons." % ref
            _logger.warning(msg)
            self.css_errors.append(msg)
            return ''
        source = re.sub(self.rx_preprocess_imports, sanitize, source)

        try:
            compiler = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        except Exception:
            msg = "Could not execute command %r" % cmd[0]
            _logger.error(msg)
            self.css_errors.append(msg)
            return ''
        result = compiler.communicate(input=source.encode('utf-8'))
        if compiler.returncode:
            error = self.get_preprocessor_error(''.join(result), source=source)
            _logger.warning(error)
            self.css_errors.append(error)
            return ''
        compiled = result[0].strip().decode('utf8')
        return compiled

    def get_preprocessor_error(self, stderr, source=None):
        """Improve and remove sensitive information from sass/less compilator error messages"""
        error = stderr.split('Load paths')[0].replace('  Use --trace for backtrace.', '')
        if 'Cannot load compass' in error:
            error += "Maybe you should install the compass gem using this extra argument:\n\n" \
                     "    $ sudo gem install compass --pre\n"
        error += "This error occured while compiling the bundle '%s' containing:" % self.xmlid
        for asset in self.stylesheets:
            if isinstance(asset, PreprocessedCSS):
                error += '\n    - %s' % (asset.url if asset.url else '<inline sass>')
        return error

class WebAsset(object):
    html_url_format = '%s'

    def __init__(self, bundle, inline=None, url=None):
        self.id = str(uuid.uuid4())
        self.bundle = bundle
        self.inline = inline
        self.url = url
        self.html_url_args = url
        self.cr = bundle.cr
        self.uid = bundle.uid
        self.registry = bundle.registry
        self.context = bundle.context
        self._content = None
        self._filename = None
        self._ir_attach = None
        name = '<inline asset>' if inline else url
        self.name = "%s defined in bundle '%s'" % (name, bundle.xmlid)
        if not inline and not url:
            raise Exception("An asset should either be inlined or url linked")

    @property
    def html_url(self):
        return self.html_url_format % self.html_url_args

    def stat(self):
        if not (self.inline or self._filename or self._ir_attach):
            path = filter(None, self.url.split('/'))
            self._filename = get_resource_path(*path)
            if self._filename:
                return
            try:
                # Test url against ir.attachments
                fields = ['__last_update', 'datas', 'mimetype']
                domain = [('type', '=', 'binary'), ('url', '=', self.url)]
                ira = self.registry['ir.attachment']
                attach = ira.search_read(self.cr, openerp.SUPERUSER_ID, domain, fields, context=self.context)
                self._ir_attach = attach[0]
            except Exception:
                raise AssetNotFound("Could not find %s" % self.name)

    def to_html(self):
        raise NotImplementedError()

    @lazy_property
    def last_modified(self):
        try:
            self.stat()
            if self._filename:
                return datetime.datetime.fromtimestamp(os.path.getmtime(self._filename))
            elif self._ir_attach:
                server_format = openerp.tools.misc.DEFAULT_SERVER_DATETIME_FORMAT
                last_update = self._ir_attach['__last_update']
                try:
                    return datetime.datetime.strptime(last_update, server_format + '.%f')
                except ValueError:
                    return datetime.datetime.strptime(last_update, server_format)
        except Exception:
            pass
        return datetime.datetime(1970, 1, 1)

    @property
    def content(self):
        if self._content is None:
            self._content = self.inline or self._fetch_content()
        return self._content

    def _fetch_content(self):
        """ Fetch content from file or database"""
        try:
            self.stat()
            if self._filename:
                with open(self._filename, 'rb') as fp:
                    return fp.read().decode('utf-8')
            else:
                return self._ir_attach['datas'].decode('base64')
        except UnicodeDecodeError:
            raise AssetError('%s is not utf-8 encoded.' % self.name)
        except IOError:
            raise AssetNotFound('File %s does not exist.' % self.name)
        except:
            raise AssetError('Could not get content for %s.' % self.name)

    def minify(self):
        return self.content

    def with_header(self, content=None):
        if content is None:
            content = self.content
        return '\n/* %s */\n%s' % (self.name, content)

class JavascriptAsset(WebAsset):
    def minify(self):
        return self.with_header(rjsmin(self.content))

    def _fetch_content(self):
        try:
            return super(JavascriptAsset, self)._fetch_content()
        except AssetError, e:
            return "console.error(%s);" % json.dumps(e.message)

    def to_html(self):
        if self.url:
            return '<script type="text/javascript" src="%s"></script>' % (self.html_url)
        else:
            return '<script type="text/javascript" charset="utf-8">%s</script>' % self.with_header()

class StylesheetAsset(WebAsset):
    rx_import = re.compile(r"""@import\s+('|")(?!'|"|/|https?://)""", re.U)
    rx_url = re.compile(r"""url\s*\(\s*('|"|)(?!'|"|/|https?://|data:)""", re.U)
    rx_sourceMap = re.compile(r'(/\*# sourceMappingURL=.*)', re.U)
    rx_charset = re.compile(r'(@charset "[^"]+";)', re.U)

    def __init__(self, *args, **kw):
        self.media = kw.pop('media', None)
        super(StylesheetAsset, self).__init__(*args, **kw)

    @property
    def content(self):
        content = super(StylesheetAsset, self).content
        if self.media:
            content = '@media %s { %s }' % (self.media, content)
        return content

    def _fetch_content(self):
        try:
            content = super(StylesheetAsset, self)._fetch_content()
            web_dir = os.path.dirname(self.url)

            if self.rx_import:
                content = self.rx_import.sub(
                    r"""@import \1%s/""" % (web_dir,),
                    content,
                )

            if self.rx_url:
                content = self.rx_url.sub(
                    r"url(\1%s/" % (web_dir,),
                    content,
                )

            if self.rx_charset:
                # remove charset declarations, we only support utf-8
                content = self.rx_charset.sub('', content)

            return content
        except AssetError, e:
            self.bundle.css_errors.append(e.message)
            return ''

    def minify(self):
        # remove existing sourcemaps, make no sense after re-mini
        content = self.rx_sourceMap.sub('', self.content)
        # comments
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.S)
        # space
        content = re.sub(r'\s+', ' ', content)
        content = re.sub(r' *([{}]) *', r'\1', content)
        return self.with_header(content)

    def to_html(self):
        media = (' media="%s"' % werkzeug.utils.escape(self.media)) if self.media else ''
        if self.url:
            href = self.html_url
            return '<link rel="stylesheet" href="%s" type="text/css"%s/>' % (href, media)
        else:
            return '<style type="text/css"%s>%s</style>' % (media, self.with_header())

class PreprocessedCSS(StylesheetAsset):
    rx_import = None

    def __init__(self, *args, **kw):
        super(PreprocessedCSS, self).__init__(*args, **kw)
        self.html_url_format = '%%s/%s/%%s.css' % self.bundle.xmlid
        self.html_url_args = tuple(self.url.rsplit('/', 1))

    def minify(self):
        return self.with_header()

    def get_source(self):
        content = self.inline or self._fetch_content()
        return "/*! %s */\n%s" % (self.id, content)

    def get_command(self):
        raise NotImplementedError

class SassStylesheetAsset(PreprocessedCSS):
    rx_indent = re.compile(r'^( +|\t+)', re.M)
    indent = None
    reindent = '    '

    def get_source(self):
        content = textwrap.dedent(self.inline or self._fetch_content())

        def fix_indent(m):
            # Indentation normalization
            ind = m.group()
            if self.indent is None:
                self.indent = ind
                if self.indent == self.reindent:
                    # Don't reindent the file if identation is the final one (reindent)
                    raise StopIteration()
            return ind.replace(self.indent, self.reindent)

        try:
            content = self.rx_indent.sub(fix_indent, content)
        except StopIteration:
            pass
        return "/*! %s */\n%s" % (self.id, content)

    def get_command(self):
        try:
            sass = find_in_path('sass')
        except IOError:
            sass = 'sass'
        return [sass, '--stdin', '-t', 'compressed', '--unix-newlines', '--compass',
                '-r', 'bootstrap-sass']

class LessStylesheetAsset(PreprocessedCSS):
    def get_command(self):
        try:
            if os.name == 'nt':
                lessc = find_in_path('lessc.cmd')
            else:
                lessc = find_in_path('lessc')
        except IOError:
            lessc = 'lessc'
        lesspath = get_resource_path('web', 'static', 'lib', 'bootstrap', 'less')
        return [lessc, '-', '--clean-css', '--no-js', '--no-color', '--include-path=%s' % lesspath]

def rjsmin(script):
    """ Minify js with a clever regex.
    Taken from http://opensource.perlig.de/rjsmin
    Apache License, Version 2.0 """
    def subber(match):
        """ Substitution callback """
        groups = match.groups()
        return (
            groups[0] or
            groups[1] or
            groups[2] or
            groups[3] or
            (groups[4] and '\n') or
            (groups[5] and ' ') or
            (groups[6] and ' ') or
            (groups[7] and ' ') or
            ''
        )

    result = re.sub(
        r'([^\047"/\000-\040]+)|((?:(?:\047[^\047\\\r\n]*(?:\\(?:[^\r\n]|\r?'
        r'\n|\r)[^\047\\\r\n]*)*\047)|(?:"[^"\\\r\n]*(?:\\(?:[^\r\n]|\r?\n|'
        r'\r)[^"\\\r\n]*)*"))[^\047"/\000-\040]*)|(?:(?<=[(,=:\[!&|?{};\r\n]'
        r')(?:[\000-\011\013\014\016-\040]|(?:/\*[^*]*\*+(?:[^/*][^*]*\*+)*/'
        r'))*((?:/(?![\r\n/*])[^/\\\[\r\n]*(?:(?:\\[^\r\n]|(?:\[[^\\\]\r\n]*'
        r'(?:\\[^\r\n][^\\\]\r\n]*)*\]))[^/\\\[\r\n]*)*/)[^\047"/\000-\040]*'
        r'))|(?:(?<=[\000-#%-,./:-@\[-^`{-~-]return)(?:[\000-\011\013\014\01'
        r'6-\040]|(?:/\*[^*]*\*+(?:[^/*][^*]*\*+)*/))*((?:/(?![\r\n/*])[^/'
        r'\\\[\r\n]*(?:(?:\\[^\r\n]|(?:\[[^\\\]\r\n]*(?:\\[^\r\n][^\\\]\r\n]'
        r'*)*\]))[^/\\\[\r\n]*)*/)[^\047"/\000-\040]*))|(?<=[^\000-!#%&(*,./'
        r':-@\[\\^`{|~])(?:[\000-\011\013\014\016-\040]|(?:/\*[^*]*\*+(?:[^/'
        r'*][^*]*\*+)*/))*(?:((?:(?://[^\r\n]*)?[\r\n]))(?:[\000-\011\013\01'
        r'4\016-\040]|(?:/\*[^*]*\*+(?:[^/*][^*]*\*+)*/))*)+(?=[^\000-\040"#'
        r'%-\047)*,./:-@\\-^`|-~])|(?<=[^\000-#%-,./:-@\[-^`{-~-])((?:[\000-'
        r'\011\013\014\016-\040]|(?:/\*[^*]*\*+(?:[^/*][^*]*\*+)*/)))+(?=[^'
        r'\000-#%-,./:-@\[-^`{-~-])|(?<=\+)((?:[\000-\011\013\014\016-\040]|'
        r'(?:/\*[^*]*\*+(?:[^/*][^*]*\*+)*/)))+(?=\+)|(?<=-)((?:[\000-\011\0'
        r'13\014\016-\040]|(?:/\*[^*]*\*+(?:[^/*][^*]*\*+)*/)))+(?=-)|(?:[\0'
        r'00-\011\013\014\016-\040]|(?:/\*[^*]*\*+(?:[^/*][^*]*\*+)*/))+|(?:'
        r'(?:(?://[^\r\n]*)?[\r\n])(?:[\000-\011\013\014\016-\040]|(?:/\*[^*'
        r']*\*+(?:[^/*][^*]*\*+)*/))*)+', subber, '\n%s\n' % script
    ).strip()
    return result
