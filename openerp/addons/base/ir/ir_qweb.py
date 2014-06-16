# -*- coding: utf-8 -*-
import collections
import cStringIO
import datetime
import hashlib
import json
import logging
import math
import os
import re
import sys
import xml  # FIXME use lxml and etree
import itertools
import lxml.html
from urlparse import urlparse

import babel
import babel.dates
from PIL import Image

import openerp.http
import openerp.tools
import openerp.tools.func
import openerp.tools.lru
from openerp.http import request
from openerp.tools.safe_eval import safe_eval as eval
from openerp.osv import osv, orm, fields
from openerp.tools import html_escape as escape
from openerp.tools.translate import _
from openerp import SUPERUSER_ID

_logger = logging.getLogger(__name__)

#--------------------------------------------------------------------
# QWeb template engine
#--------------------------------------------------------------------
class QWebException(Exception):
    def __init__(self, message, **kw):
        Exception.__init__(self, message)
        self.qweb = dict(kw)

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

class QWebContext(dict):
    def __init__(self, cr, uid, data, loader=None, templates=None, context=None):
        self.cr = cr
        self.uid = uid
        self.loader = loader
        self.templates = templates or {}
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
        return QWebContext(self.cr, self.uid, dict.copy(self),
                           loader=self.loader,
                           templates=self.templates,
                           context=self.context)

    def __copy__(self):
        return self.copy()

class QWeb(orm.AbstractModel):
    """QWeb Xml templating engine

    The templating engine use a very simple syntax based "magic" xml
    attributes, to produce textual output (even non-xml).

    The core magic attributes are:

    flow attributes:
        t-if t-foreach t-call

    output attributes:
        t-att t-raw t-esc t-trim

    assignation attribute:
        t-set

    QWeb can be extended like any OpenERP model and new attributes can be
    added.

    If you need to customize t-fields rendering, subclass the ir.qweb.field
    model (and its sub-models) then override :meth:`~.get_converter_for` to
    fetch the right field converters for your qweb model.

    Beware that if you need extensions or alterations which could be
    incompatible with other subsystems, you should create a local object
    inheriting from ``ir.qweb`` and customize that.
    """

    _name = 'ir.qweb'

    node = xml.dom.Node
    _void_elements = frozenset([
        'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'keygen',
        'link', 'menuitem', 'meta', 'param', 'source', 'track', 'wbr'])
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

    def add_template(self, qwebcontext, name, node):
        """Add a parsed template in the context. Used to preprocess templates."""
        qwebcontext.templates[name] = node

    def load_document(self, document, res_id, qwebcontext):
        """
        Loads an XML document and installs any contained template in the engine
        """
        if hasattr(document, 'documentElement'):
            dom = document
        elif document.startswith("<?xml"):
            dom = xml.dom.minidom.parseString(document)
        else:
            dom = xml.dom.minidom.parse(document)

        for node in dom.documentElement.childNodes:
            if node.nodeType == self.node.ELEMENT_NODE:
                if node.getAttribute('t-name'):
                    name = str(node.getAttribute("t-name"))
                    self.add_template(qwebcontext, name, node)
                if res_id and node.tagName == "t":
                    self.add_template(qwebcontext, res_id, node)
                    res_id = None

    def get_template(self, name, qwebcontext):
        origin_template = qwebcontext.get('__caller__') or qwebcontext['__stack__'][0]
        if qwebcontext.loader and name not in qwebcontext.templates:
            try:
                xml_doc = qwebcontext.loader(name)
            except ValueError:
                raise_qweb_exception(QWebTemplateNotFound, message="Loader could not find template %r" % name, template=origin_template)
            self.load_document(xml_doc, isinstance(name, (int, long)) and name or None, qwebcontext=qwebcontext)

        if name in qwebcontext.templates:
            return qwebcontext.templates[name]

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
        return self.render_node(self.get_template(id_or_xml_id, qwebcontext), qwebcontext)

    def render_node(self, element, qwebcontext):
        result = ""
        if element.nodeType == self.node.TEXT_NODE or element.nodeType == self.node.CDATA_SECTION_NODE:
            result = element.data.encode("utf8")
        elif element.nodeType == self.node.ELEMENT_NODE:
            generated_attributes = ""
            t_render = None
            template_attributes = {}
            for (attribute_name, attribute_value) in element.attributes.items():
                attribute_name = str(attribute_name)
                if attribute_name == "groups":
                    cr = qwebcontext.get('request') and qwebcontext['request'].cr or None
                    uid = qwebcontext.get('request') and qwebcontext['request'].uid or None
                    can_see = self.user_has_groups(cr, uid, groups=attribute_value) if cr and uid else False
                    if not can_see:
                        return ''
                    continue

                if isinstance(attribute_value, unicode):
                    attribute_value = attribute_value.encode("utf8")
                else:
                    attribute_value = attribute_value.nodeValue.encode("utf8")

                if attribute_name.startswith("t-"):
                    for attribute in self._render_att:
                        if attribute_name[2:].startswith(attribute):
                            att, val = self._render_att[attribute](self, element, attribute_name, attribute_value, qwebcontext)
                            generated_attributes += val and ' %s="%s"' % (att, escape(val)) or " "
                            break
                    else:
                        if attribute_name[2:] in self._render_tag:
                            t_render = attribute_name[2:]
                        template_attributes[attribute_name[2:]] = attribute_value
                else:
                    generated_attributes += ' %s="%s"' % (attribute_name, escape(attribute_value))

            if 'debug' in template_attributes:
                debugger = template_attributes.get('debug', 'pdb')
                __import__(debugger).set_trace()  # pdb, ipdb, pudb, ...
            if t_render:
                result = self._render_tag[t_render](self, element, template_attributes, generated_attributes, qwebcontext)
            else:
                result = self.render_element(element, template_attributes, generated_attributes, qwebcontext)
        if isinstance(result, unicode):
            return result.encode('utf-8')
        return result

    def render_element(self, element, template_attributes, generated_attributes, qwebcontext, inner=None):
        # element: element
        # template_attributes: t-* attributes
        # generated_attributes: generated attributes
        # qwebcontext: values
        # inner: optional innerXml
        if inner:
            g_inner = inner
        else:
            g_inner = []
            for current_node in element.childNodes:
                try:
                    g_inner.append(self.render_node(current_node, qwebcontext))
                except QWebException:
                    raise
                except Exception:
                    template = qwebcontext.get('__template__')
                    raise_qweb_exception(message="Could not render element %r" % element.nodeName, node=element, template=template)
        name = str(element.nodeName)
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
            return "<%s%s/>" % (name, generated_attributes)

    # Attributes
    def render_att_att(self, element, attribute_name, attribute_value, qwebcontext):
        if attribute_name.startswith("t-attf-"):
            att, val = attribute_name[7:], self.eval_format(attribute_value, qwebcontext)
        elif attribute_name.startswith("t-att-"):
            att, val = attribute_name[6:], self.eval(attribute_value, qwebcontext)
        else:
            att, val = self.eval_object(attribute_value, qwebcontext)
        if val and not isinstance(val, str):
            val = unicode(val).encode("utf8")
        return att, val

    # Tags
    def render_tag_raw(self, element, template_attributes, generated_attributes, qwebcontext):
        inner = self.eval_str(template_attributes["raw"], qwebcontext)
        return self.render_element(element, template_attributes, generated_attributes, qwebcontext, inner)

    def render_tag_esc(self, element, template_attributes, generated_attributes, qwebcontext):
        options = json.loads(template_attributes.get('esc-options') or '{}')
        widget = self.get_widget_for(options.get('widget', ''))
        inner = widget.format(template_attributes['esc'], options, qwebcontext)
        return self.render_element(element, template_attributes, generated_attributes, qwebcontext, inner)

    def render_tag_foreach(self, element, template_attributes, generated_attributes, qwebcontext):
        expr = template_attributes["foreach"]
        enum = self.eval_object(expr, qwebcontext)
        if enum is not None:
            var = template_attributes.get('as', expr).replace('.', '_')
            copy_qwebcontext = qwebcontext.copy()
            size = -1
            if isinstance(enum, (list, tuple)):
                size = len(enum)
            elif hasattr(enum, 'count'):
                size = enum.count()
            copy_qwebcontext["%s_size" % var] = size
            copy_qwebcontext["%s_all" % var] = enum
            index = 0
            ru = []
            for i in enum:
                copy_qwebcontext["%s_value" % var] = i
                copy_qwebcontext["%s_index" % var] = index
                copy_qwebcontext["%s_first" % var] = index == 0
                copy_qwebcontext["%s_even" % var] = index % 2
                copy_qwebcontext["%s_odd" % var] = (index + 1) % 2
                copy_qwebcontext["%s_last" % var] = index + 1 == size
                if index % 2:
                    copy_qwebcontext["%s_parity" % var] = 'odd'
                else:
                    copy_qwebcontext["%s_parity" % var] = 'even'
                if 'as' in template_attributes:
                    copy_qwebcontext[var] = i
                elif isinstance(i, dict):
                    copy_qwebcontext.update(i)
                ru.append(self.render_element(element, template_attributes, generated_attributes, copy_qwebcontext))
                index += 1
            return "".join(ru)
        else:
            template = qwebcontext.get('__template__')
            raise QWebException("foreach enumerator %r is not defined while rendering template %r" % (expr, template), template=template)

    def render_tag_if(self, element, template_attributes, generated_attributes, qwebcontext):
        if self.eval_bool(template_attributes["if"], qwebcontext):
            return self.render_element(element, template_attributes, generated_attributes, qwebcontext)
        return ""

    def render_tag_call(self, element, template_attributes, generated_attributes, qwebcontext):
        d = qwebcontext.copy()
        d[0] = self.render_element(element, template_attributes, generated_attributes, d)
        cr = d.get('request') and d['request'].cr or None
        uid = d.get('request') and d['request'].uid or None

        template = self.eval_format(template_attributes["call"], d)
        try:
            template = int(template)
        except ValueError:
            pass
        return self.render(cr, uid, template, d)

    def render_tag_call_assets(self, element, template_attributes, generated_attributes, qwebcontext):
        """ This special 't-call' tag can be used in order to aggregate/minify javascript and css assets"""
        name = template_attributes['call-assets']

        # Backward compatibility hack for manifest usage
        qwebcontext['manifest_list'] = openerp.addons.web.controllers.main.manifest_list

        d = qwebcontext.copy()
        d.context['inherit_branding'] = False
        content = self.render_tag_call(
            element, {'call': name}, generated_attributes, d)
        bundle = AssetsBundle(name, html=content)
        css = self.get_attr_bool(template_attributes.get('css'), default=True)
        js = self.get_attr_bool(template_attributes.get('js'), default=True)
        return bundle.to_html(css=css, js=js, debug=bool(qwebcontext.get('debug')))

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
        node_name = element.nodeName
        assert node_name not in ("table", "tbody", "thead", "tfoot", "tr", "td",
                                 "li", "ul", "ol", "dl", "dt", "dd"),\
            "RTE widgets do not work correctly on %r elements" % node_name
        assert node_name != 't',\
            "t-field can not be used on a t element, provide an actual HTML node"

        record, field_name = template_attributes["field"].rsplit('.', 1)
        record = self.eval_object(record, qwebcontext)

        column = record._model._all_columns[field_name].column
        options = json.loads(template_attributes.get('field-options') or '{}')
        field_type = get_field_type(column, options)

        converter = self.get_converter_for(field_type)

        return converter.to_html(qwebcontext.cr, qwebcontext.uid, field_name, record, options,
                                 element, template_attributes, generated_attributes, qwebcontext, context=qwebcontext.context)

    def get_converter_for(self, field_type):
        return self.pool.get('ir.qweb.field.' + field_type, self.pool['ir.qweb.field'])

    def get_widget_for(self, widget):
        return self.pool.get('ir.qweb.widget.' + widget, self.pool['ir.qweb.widget'])

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
        """
        Generates the metadata attributes (prefixed by ``data-oe-`` for the
        root node of the field conversion. Attribute values are escaped by the
        parent.

        The default attributes are:

        * ``model``, the name of the record's model
        * ``id`` the id of the record to which the field belongs
        * ``field`` the name of the converted field
        * ``type`` the logical field type (widget, may not match the column's
          ``type``, may not be any _column subclass name)
        * ``translate``, a boolean flag (``0`` or ``1``) denoting whether the
          column is translatable
        * ``expression``, the original expression

        :returns: iterable of (attribute name, attribute value) pairs.
        """
        column = record._model._all_columns[field_name].column
        field_type = get_field_type(column, options)
        return [
            ('data-oe-model', record._model._name),
            ('data-oe-id', record.id),
            ('data-oe-field', field_name),
            ('data-oe-type', field_type),
            ('data-oe-expression', t_att['field']),
        ]

    def value_to_html(self, cr, uid, value, column, options=None, context=None):
        """ Converts a single value to its HTML version/output
        """
        if not value: return ''
        return value

    def record_to_html(self, cr, uid, field_name, record, column, options=None, context=None):
        """ Converts the specified field of the browse_record ``record`` to
        HTML
        """
        return self.value_to_html(
            cr, uid, record[field_name], column, options=options, context=context)

    def to_html(self, cr, uid, field_name, record, options,
                source_element, t_att, g_att, qweb_context, context=None):
        """ Converts a ``t-field`` to its HTML output. A ``t-field`` may be
        extended by a ``t-field-options``, which is a JSON-serialized mapping
        of configuration values.

        A default configuration key is ``widget`` which can override the
        field's own ``_type``.
        """
        try:
            content = self.record_to_html(
                cr, uid, field_name, record,
                record._model._all_columns[field_name].column,
                options, context=context)
            if options.get('html-escape', True):
                content = escape(content)
            elif hasattr(content, '__html__'):
                content = content.__html__()
        except Exception:
            _logger.warning("Could not get field %s for model %s",
                            field_name, record._model._name, exc_info=True)
            content = None

        if context and context.get('inherit_branding'):
            # add branding attributes
            g_att += ''.join(
                ' %s="%s"' % (name, escape(value))
                for name, value in self.attributes(
                    cr, uid, field_name, record, options,
                    source_element, g_att, t_att, qweb_context)
            )

        return self.render_element(cr, uid, source_element, t_att, g_att,
                                   qweb_context, content)

    def qweb_object(self):
        return self.pool['ir.qweb']

    def render_element(self, cr, uid, source_element, t_att, g_att,
                       qweb_context, content):
        """ Final rendering hook, by default just calls ir.qweb's ``render_element``
        """
        return self.qweb_object().render_element(
            source_element, t_att, g_att, qweb_context, content or '')

    def user_lang(self, cr, uid, context):
        """
        Fetches the res.lang object corresponding to the language code stored
        in the user's context. Fallbacks to en_US if no lang is present in the
        context *or the language code is not valid*.

        :returns: res.lang browse_record
        """
        if context is None: context = {}

        lang_code = context.get('lang') or 'en_US'
        Lang = self.pool['res.lang']

        lang_ids = Lang.search(cr, uid, [('code', '=', lang_code)], context=context) \
               or  Lang.search(cr, uid, [('code', '=', 'en_US')], context=context)

        return Lang.browse(cr, uid, lang_ids[0], context=context)

class FloatConverter(osv.AbstractModel):
    _name = 'ir.qweb.field.float'
    _inherit = 'ir.qweb.field'

    def precision(self, cr, uid, column, options=None, context=None):
        _, precision = column.digits or (None, None)
        return precision

    def value_to_html(self, cr, uid, value, column, options=None, context=None):
        if context is None:
            context = {}
        precision = self.precision(cr, uid, column, options=options, context=context)
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

    def value_to_html(self, cr, uid, value, column, options=None, context=None):
        if not value: return ''
        lang = self.user_lang(cr, uid, context=context)
        locale = babel.Locale.parse(lang.code)

        if isinstance(value, basestring):
            value = datetime.datetime.strptime(
                value, openerp.tools.DEFAULT_SERVER_DATE_FORMAT)

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

    def value_to_html(self, cr, uid, value, column, options=None, context=None):
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

    def value_to_html(self, cr, uid, value, column, options=None, context=None):
        """
        Escapes the value and converts newlines to br. This is bullshit.
        """
        if not value: return ''

        return nl2br(value, options=options)

class SelectionConverter(osv.AbstractModel):
    _name = 'ir.qweb.field.selection'
    _inherit = 'ir.qweb.field'

    def record_to_html(self, cr, uid, field_name, record, column, options=None, context=None):
        value = record[field_name]
        if not value: return ''
        selection = dict(fields.selection.reify(
            cr, uid, record._model, column))
        return self.value_to_html(
            cr, uid, selection[value], column, options=options)

class ManyToOneConverter(osv.AbstractModel):
    _name = 'ir.qweb.field.many2one'
    _inherit = 'ir.qweb.field'

    def record_to_html(self, cr, uid, field_name, record, column, options=None, context=None):
        [read] = record.read([field_name])
        if not read[field_name]: return ''
        _, value = read[field_name]
        return nl2br(value, options=options)

class HTMLConverter(osv.AbstractModel):
    _name = 'ir.qweb.field.html'
    _inherit = 'ir.qweb.field'

    def value_to_html(self, cr, uid, value, column, options=None, context=None):
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

    def value_to_html(self, cr, uid, value, column, options=None, context=None):
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
    ``display_currency``.

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

    def record_to_html(self, cr, uid, field_name, record, column, options, context=None):
        if context is None:
            context = {}
        Currency = self.pool['res.currency']
        display = self.display_currency(cr, uid, options)

        # lang.format mandates a sprintf-style format. These formats are non-
        # minimal (they have a default fixed precision instead), and
        # lang.format will not set one by default. currency.round will not
        # provide one either. So we need to generate a precision value
        # (integer > 0) from the currency's rounding (a float generally < 1.0).
        #
        # The log10 of the rounding should be the number of digits involved if
        # negative, if positive clamp to 0 digits and call it a day.
        # nb: int() ~ floor(), we want nearest rounding instead
        precision = int(round(math.log10(display.rounding)))
        fmt = "%.{0}f".format(-precision if precision < 0 else 0)

        lang_code = context.get('lang') or 'en_US'
        lang = self.pool['res.lang']
        formatted_amount = lang.format(cr, uid, [lang_code], 
            fmt, Currency.round(cr, uid, display, record[field_name]),
            grouping=True, monetary=True)

        pre = post = u''
        if display.position == 'before':
            pre = u'{symbol} '
        else:
            post = u' {symbol}'

        return HTMLSafe(u'{pre}<span class="oe_currency_value">{0}</span>{post}'.format(
            formatted_amount,
            pre=pre, post=post,
        ).format(
            symbol=display.symbol,
        ))

    def display_currency(self, cr, uid, options):
        return self.qweb_object().eval_object(
            options['display_currency'], options['_qweb_context'])

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

    def value_to_html(self, cr, uid, value, column, options=None, context=None):
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

    def value_to_html(self, cr, uid, value, column, options=None, context=None):
        parse_format = openerp.tools.DEFAULT_SERVER_DATETIME_FORMAT
        locale = babel.Locale.parse(
            self.user_lang(cr, uid, context=context).code)

        if isinstance(value, basestring):
            value = datetime.datetime.strptime(value, parse_format)

        # value should be a naive datetime in UTC. So is fields.datetime.now()
        reference = datetime.datetime.strptime(column.now(), parse_format)

        return babel.dates.format_timedelta(
            value - reference, add_direction=True, locale=locale)

class Contact(orm.AbstractModel):
    _name = 'ir.qweb.field.contact'
    _inherit = 'ir.qweb.field.many2one'

    def record_to_html(self, cr, uid, field_name, record, column, options=None, context=None):
        if options is None:
            options = {}
        opf = options.get('fields') or ["name", "address", "phone", "mobile", "fax", "email"]

        if not getattr(record, field_name):
            return None

        id = getattr(record, field_name).id
        field_browse = self.pool[column._obj].browse(cr, openerp.SUPERUSER_ID, id, context={"show_address": True})
        value = field_browse.name_get()[0][1]

        val = {
            'name': value.split("\n")[0],
            'address': escape("\n".join(value.split("\n")[1:])),
            'phone': field_browse.phone,
            'mobile': field_browse.mobile,
            'fax': field_browse.fax,
            'city': field_browse.city,
            'country_id': field_browse.country_id and field_browse.country_id.name_get()[0][1],
            'website': field_browse.website,
            'email': field_browse.email,
            'fields': opf,
            'object': field_browse,
            'options': options
        }

        html = self.pool["ir.ui.view"].render(cr, uid, "base.contact", val, engine='ir.qweb', context=context).decode('utf8')

        return HTMLSafe(html)

class QwebView(orm.AbstractModel):
    _name = 'ir.qweb.field.qweb'
    _inherit = 'ir.qweb.field.many2one'

    def record_to_html(self, cr, uid, field_name, record, column, options=None, context=None):
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
            pre = u'{symbol} '
        else:
            post = u' {symbol}'

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

def get_field_type(column, options):
    """ Gets a t-field's effective type from the field's column and its options
    """
    return options.get('widget', column._type)

class AssetsBundle(object):
    cache = openerp.tools.lru.LRU(32)
    rx_css_import = re.compile("(@import[^;{]+;?)", re.M)

    def __init__(self, xmlid, html=None, debug=False):
        self.debug = debug
        self.xmlid = xmlid
        self.javascripts = []
        self.stylesheets = []
        self.remains = []
        self._checksum = None
        if html:
            self.parse(html)

    def parse(self, html):
        fragments = lxml.html.fragments_fromstring(html)
        for el in fragments:
            if isinstance(el, basestring):
                self.remains.append(el)
            elif isinstance(el, lxml.html.HtmlElement):
                src = el.get('src')
                href = el.get('href')
                if el.tag == 'style':
                    self.stylesheets.append(StylesheetAsset(source=el.text))
                elif el.tag == 'link' and el.get('rel') == 'stylesheet' and self.can_aggregate(href):
                    self.stylesheets.append(StylesheetAsset(url=href))
                elif el.tag == 'script' and not src:
                    self.javascripts.append(JavascriptAsset(source=el.text))
                elif el.tag == 'script' and self.can_aggregate(src):
                    self.javascripts.append(JavascriptAsset(url=src))
                else:
                    self.remains.append(lxml.html.tostring(el))
            else:
                try:
                    self.remains.append(lxml.html.tostring(el))
                except Exception:
                    # notYETimplementederror
                    raise NotImplementedError

    def can_aggregate(self, url):
        return not urlparse(url).netloc and not url.startswith(('/web/css', '/web/js'))

    def to_html(self, sep='\n            ', css=True, js=True, debug=False):
        response = []
        if debug:
            if css:
                for style in self.stylesheets:
                    response.append(style.to_html())
            if js:
                for jscript in self.javascripts:
                    response.append(jscript.to_html())
        else:
            if css and self.stylesheets:
                response.append('<link href="/web/css/%s" rel="stylesheet"/>' % self.xmlid)
            if js and self.javascripts:
                response.append('<script type="text/javascript" src="/web/js/%s"></script>' % self.xmlid)
        response.extend(self.remains)
        return sep + sep.join(response)

    @openerp.tools.func.lazy_property
    def last_modified(self):
        return max(itertools.chain(
            (asset.last_modified for asset in self.javascripts),
            (asset.last_modified for asset in self.stylesheets),
            [datetime.datetime(1970, 1, 1)],
        ))

    @openerp.tools.func.lazy_property
    def checksum(self):
        checksum = hashlib.new('sha1')
        for asset in itertools.chain(self.javascripts, self.stylesheets):
            checksum.update(asset.content.encode("utf-8"))
        return checksum.hexdigest()

    def js(self):
        key = 'js_' + self.checksum
        if key not in self.cache:
            content =';\n'.join(asset.minify() for asset in self.javascripts)
            self.cache[key] = content
        if self.debug:
            return "/*\n%s\n*/\n" % '\n'.join(
                [asset.url for asset in self.javascripts if asset.url]) + self.cache[key]
        return self.cache[key]

    def css(self):
        key = 'css_' + self.checksum
        if key not in self.cache:
            content = '\n'.join(asset.minify() for asset in self.stylesheets)
            # move up all @import rules to the top
            matches = []
            def push(matchobj):
                matches.append(matchobj.group(0))
                return ''

            content = re.sub(self.rx_css_import, push, content)

            matches.append(content)
            content = u'\n'.join(matches)
            self.cache[key] = content
        if self.debug:
            return "/*\n%s\n*/\n" % '\n'.join(
                [asset.url for asset in self.javascripts if asset.url]) + self.cache[key]
        return self.cache[key]

class WebAsset(object):
    def __init__(self, source=None, url=None):
        self.source = source
        self.url = url
        self._irattach = None
        self._content = None
        self.filename = None
        self.last_modified = None
        if source:
            self.last_modified = datetime.datetime(1970, 1, 1)
        if url:
            module = filter(None, self.url.split('/'))[0]
            try:
                # Test url against modules static assets
                mpath = openerp.http.addons_manifest[module]['addons_path']
                self.filename = mpath + self.url.replace('/', os.path.sep)
                self.last_modified = datetime.datetime.fromtimestamp(os.path.getmtime(self.filename))
            except Exception:
                try:
                    # Test url against ir.attachments
                    domain = [('type', '=', 'binary'), ('url', '=', self.url)]
                    attach = request.registry['ir.attachment'].search_read(request.cr, SUPERUSER_ID, domain, ['__last_update', 'datas', 'mimetype'], context=request.context)
                    self._irattach = attach[0]
                    server_format = openerp.tools.misc.DEFAULT_SERVER_DATETIME_FORMAT
                    try:
                        self.last_modified =  datetime.datetime.strptime(attach[0]['__last_update'], server_format + '.%f')
                    except ValueError:
                        self.last_modified =  datetime.datetime.strptime(attach[0]['__last_update'], server_format)
                except Exception:
                    raise KeyError("Could not find asset '%s' for '%s' addon" % (self.url, module))

    @openerp.tools.func.lazy_property
    def content(self):
        if self.source:
            return self.source
        if self._irattach:
            return self._irattach['datas'].decode('base64')
        return self.get_content()

    def get_content(self):
        with open(self.filename, 'rb') as fp:
            return fp.read().decode('utf-8')

    def minify(self):
        return self.content

class JavascriptAsset(WebAsset):
    def minify(self):
        return rjsmin(self.content)

    def to_html(self):
        if self.url:
            return '<script type="text/javascript" src="%s"></script>' % self.url
        else:
            return '<script type="text/javascript" charset="utf-8">%s</script>' % self.source

class StylesheetAsset(WebAsset):
    rx_import = re.compile(r"""@import\s+('|")(?!'|"|/|https?://)""", re.U)
    rx_url = re.compile(r"""url\s*\(\s*('|"|)(?!'|"|/|https?://|data:)""", re.U)
    rx_sourceMap = re.compile(r'(/\*# sourceMappingURL=.*)', re.U)

    def _get_content(self):
        with open(self.filename, 'rb') as fp:
            firstline = fp.readline()
            m = re.match(r'@charset "([^"]+)";', firstline)
            if m:
                encoding = m.group(1)
            else:
                encoding = "utf-8"
                # "reinject" first line as it's not @charset
                fp.seek(0)

            return fp.read().decode(encoding)

    def get_content(self):
        content = self._get_content()
        if self.url:
            web_dir = os.path.dirname(self.url)

            content = self.rx_import.sub(
                r"""@import \1%s/""" % (web_dir,),
                content,
            )

            content = self.rx_url.sub(
                r"url(\1%s/" % (web_dir,),
                content,
            )
        return content

    def minify(self):
        # remove existing sourcemaps, make no sense after re-mini
        content = self.rx_sourceMap.sub('', self.content)
        # comments
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.S)
        # space
        content = re.sub(r'\s+', ' ', content)
        content = re.sub(r' *([{}]) *', r'\1', content)
        return content

    def to_html(self):
        if self.url:
            return '<link rel="stylesheet" href="%s" type="text/css"/>' % self.url
        else:
            return '<style type="text/css">%s</style>' % self.source

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

# vim:et:
