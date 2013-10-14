# -*- coding: utf-8 -*-
import cStringIO
import json
import datetime
import dateutil
import logging
import re
import traceback
import urllib
import xml # FIXME use lxml and etree

import Image
import werkzeug.utils

from openerp.osv import osv, orm, fields

_logger = logging.getLogger(__name__)

BUILTINS = {
    'False': False,
    'None': None,
    'True': True,
    'abs': abs,
    'bool': bool,
    'dict': dict,
    'filter': filter,
    'len': len,
    'list': list,
    'map': map,
    'max': max,
    'min': min,
    'reduce': reduce,
    'repr': repr,
    'round': round,
    'set': set,
    'str': str,
    'tuple': tuple,
    'quote':  urllib.quote,
    'urlencode': urllib.urlencode,
    'datetime': datetime,
    # dateutil.relativedelta is an old-style class and cannot be directly
    # instanciated wihtin a jinja2 expression, so a lambda "proxy" is
    # is needed, apparently.
    'relativedelta': lambda *a, **kw : dateutil.relativedelta.relativedelta(*a, **kw),
}

## We use a jinja2 sandboxed environment to render qWeb templates.
#from openerp.tools.safe_eval import safe_eval as eval
#from jinja2.sandbox import SandboxedEnvironment
#from jinja2.exceptions import SecurityError, UndefinedError
#UNSAFE = ["browse", "search", "read", "unlink", "read_group"]
#SAFE = ["_name"]

class QWebContext(dict):
    def __init__(self, data, undefined_handler=None, loader=None):
        self.loader = loader
        self.undefined_handler = undefined_handler
        dic = BUILTINS.copy()
        dic.update(data)
        super(QWebContext, self).__init__(dic)
        self['defined'] = lambda key: key in self

    def __getitem__(self, key):
        if key in self:
            return self.get(key)
        elif not self.undefined_handler:
            raise NameError("QWeb: name %r is not defined while rendering template %r" % (key, self.get('__template__')))
        else:
            return self.get(key, self.undefined_handler(key, self))

    def safe_eval(self, expr):
        # This is too slow, we should cached compiled expressions attribute of
        # qweb to will be changed into a model object ir.qweb.
        #
        # The cache should be on qweb, and qweb context contructor take qweb as
        # argument to store the cache.
        #
        #class QWebSandboxedEnvironment(SandboxedEnvironment):
        #    def is_safe_attribute(self, obj, attr, value):
        #        if str(attr) in SAFE:
        #            res = True
        #        else:
        #            res = super(QWebSandboxedEnvironment, self).is_safe_attribute(obj, attr, value)
        #            if str(attr) in UNSAFE or not res:
        #                raise SecurityError("access to attribute '%s' of '%s' object is unsafe." % (attr,obj))
        #        return res
        #env = qWebSandboxedEnvironment(variable_start_string="${", variable_end_string="}")
        #env.globals.update(context)
        #env.compile_expression(expr)()
        return eval(expr, None, self)

    def copy(self):
        return QWebContext(dict.copy(self),
                           undefined_handler=self.undefined_handler,
                           loader=self.loader)

    def __copy__(self):
        return self.copy()

class QWeb(orm.AbstractModel):
    """QWeb Xml templating engine

    The templating engine use a very simple syntax, "magic" xml attributes, to
    produce any kind of texutal output (even non-xml).

    QWebXml:
        the template engine core implements the basic magic attributes:

        t-att t-raw t-esc t-if t-foreach t-set t-call t-trim


    - loader: function that return a template

    QWeb rendering can be used for many tasks. As a result, customizations
    made by one task context (to either the main qweb rendering or to specific
    fields rendering) could break other tasks.

    To avoid that, ``ir.qweb`` was consciously made inheritable and the "root"
    of an object hierarchy. If you need extensions or alterations which could
    be incompatible with other subsystems, you should create a local object
    inheriting from ``ir.qweb`` and customize that.

    If you need to customize t-fields rendering, subclass the ir.qweb.field
    model (and its sub-models) then override :meth:`~.get_converter_for` to
    fetch the right field converters for your qweb model.
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
        self._t = {}

        self._render_tag = self.prefixed_methods('render_tag_')
        self._render_att = self.prefixed_methods('render_att_')

    def prefixed_methods(self, prefix):
        """ Extracts all methods prefixed by ``prefix``, and returns a mapping
        of (t-name, method) where the t-name is the method name with prefix
        removed and underscore converted to dashes

        :param str prefix:
        :return: dict
        """
        return dict(
            (name[len(prefix):].replace('_', '-'), getattr(type(self), name))
            for name in dir(self)
            if name.startswith(prefix))

    def register_tag(self, tag, func):
        self._render_tag[tag] = func

    def load_document(self, x):
        """
        Loads an XML document and installs any contained template in the engine
        """
        if hasattr(x, 'documentElement'):
            dom = x
        elif x.startswith("<?xml"):
            dom = xml.dom.minidom.parseString(x)
        else:
            dom = xml.dom.minidom.parse(x)

        for n in dom.documentElement.childNodes:
            if n.nodeType == self.node.ELEMENT_NODE and n.getAttribute('t-name'):
                self._t[str(n.getAttribute("t-name"))] = n

    def get_template(self, name, context):
        if context.loader and name not in self._t:
            xml_doc = context.loader(name)
            self.load_document(xml_doc)

        if name in self._t:
            return self._t[name]

        raise KeyError('qweb: template "%s" not found' % name)

    def eval(self, expr, v):
        try:
            return v.safe_eval(expr)
        except (osv.except_osv, orm.except_orm), err:
            raise orm.except_orm("QWeb Error", "Invalid expression %r while rendering template '%s'.\n\n%s" % (expr, v.get('__template__'), err[1]))
        except Exception:
            raise SyntaxError("QWeb: invalid expression %r while rendering template '%s'.\n\n%s" % (expr, v.get('__template__'), traceback.format_exc()))

    def eval_object(self, expr, v):
        return self.eval(expr, v)

    def eval_str(self, expr, v):
        if expr == "0":
            return v.get(0, '')
        val = self.eval(expr, v)
        if isinstance(val, unicode):
            return val.encode("utf8")
        return str(val)

    def eval_format(self, expr, v):
        expr, replacements = self._format_regex.subn(
            lambda m: self.eval_str(m.group(1) or m.group(2), v),
            expr)

        if replacements:
            return expr

        try:
            return str(expr % v)
        except:
            raise Exception("QWeb: format error '%s' " % expr)

    def eval_bool(self, expr, v):
        val = self.eval(expr, v)
        if val:
            return 1
        else:
            return 0

    def render(self, tname, v=None, out=None, loader=None, undefined_handler=None):
        if v is None:
            v = {}
        if not isinstance(v, QWebContext):
            v = QWebContext(v, undefined_handler=undefined_handler, loader=loader)
        v['__template__'] = tname
        stack = v.get('__stack__', [])
        if stack:
            v['__caller__'] = stack[-1]
        stack.append(tname)
        v['__stack__'] = stack
        v['xmlid'] = str(stack[0]) # Temporary fix
        return self.render_node(self.get_template(tname, v), v)

    def render_node(self, e, v):
        r = ""
        if e.nodeType == self.node.TEXT_NODE or e.nodeType == self.node.CDATA_SECTION_NODE:
            r = e.data.encode("utf8")
        elif e.nodeType == self.node.ELEMENT_NODE:
            g_att = ""
            t_render = None
            t_att = {}
            for (an, av) in e.attributes.items():
                an = str(an)
                if isinstance(av, unicode):
                    av = av.encode("utf8")
                else:
                    av = av.nodeValue.encode("utf8")
                if an.startswith("t-"):
                    for i in self._render_att:
                        if an[2:].startswith(i):
                            g_att += self._render_att[i](self, e, an, av, v)
                            break
                    else:
                        if an[2:] in self._render_tag:
                            t_render = an[2:]
                        t_att[an[2:]] = av
                else:
                    g_att += ' %s="%s"' % (an, werkzeug.utils.escape(av))

            if 'debug' in t_att:
                debugger = t_att.get('debug', 'pdb')
                __import__(debugger).set_trace() # pdb, ipdb, pudb, ...
            if t_render:
                r = self._render_tag[t_render](self, e, t_att, g_att, v)
            else:
                r = self.render_element(e, t_att, g_att, v)
        if isinstance(r, unicode):
            return r.encode('utf-8')
        return r

    def render_element(self, e, t_att, g_att, v, inner=None):
        # e: element
        # t_att: t-* attributes
        # g_att: generated attributes
        # v: values
        # inner: optional innerXml
        if inner:
            g_inner = inner
        else:
            g_inner = []
            for n in e.childNodes:
                g_inner.append(self.render_node(n, v))
        name = str(e.nodeName)
        inner = "".join(g_inner)
        trim = t_att.get("trim", 0)
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
                v if isinstance(v, str) else v.encode('utf-8')
                for v in (name, g_att, inner, name))
        else:
            return "<%s%s/>" % (name, g_att)

    # Attributes
    def render_att_att(self, e, an, av, v):
        if an.startswith("t-attf-"):
            att, val = an[7:], self.eval_format(av, v)
        elif an.startswith("t-att-"):
            att, val = an[6:], self.eval(av, v)
            if isinstance(val, unicode):
                val = val.encode("utf8")
        else:
            att, val = self.eval_object(av, v)
        return val and ' %s="%s"' % (att, werkzeug.utils.escape(val)) or " "

    def render_att_href(self, e, an, av, v):
        return self.url_for(e, an, av, v)
    def render_att_src(self, e, an, av, v):
        return self.url_for(e, an, av, v)
    def render_att_action(self, e, an, av, v):
        return self.url_for(e, an, av, v)
    def url_for(self, e, an, av, v):
        if 'url_for' not in v:
            raise KeyError("qweb: no 'url_for' found in context")
        path = str(v['url_for'](self.eval_format(av, v)))
        return ' %s="%s"' % (an[2:], werkzeug.utils.escape(path))

    # Tags
    def render_tag_raw(self, e, t_att, g_att, v):
        inner = self.eval_str(t_att["raw"], v)
        return self.render_element(e, t_att, g_att, v, inner)

    def render_tag_rawf(self, e, t_att, g_att, v):
        inner = self.eval_format(t_att["rawf"], v)
        return self.render_element(e, t_att, g_att, v, inner)

    def render_tag_esc(self, e, t_att, g_att, v):
        inner = werkzeug.utils.escape(self.eval_str(t_att["esc"], v))
        return self.render_element(e, t_att, g_att, v, inner)

    def render_tag_escf(self, e, t_att, g_att, v):
        inner = werkzeug.utils.escape(self.eval_format(t_att["escf"], v))
        return self.render_element(e, t_att, g_att, v, inner)

    def render_tag_foreach(self, e, t_att, g_att, v):
        expr = t_att["foreach"]
        enum = self.eval_object(expr, v)
        if enum is not None:
            var = t_att.get('as', expr).replace('.', '_')
            d = v.copy()
            size = -1
            if isinstance(enum, (list, tuple)):
                size = len(enum)
            elif hasattr(enum, 'count'):
                size = enum.count()
            d["%s_size" % var] = size
            d["%s_all" % var] = enum
            index = 0
            ru = []
            for i in enum:
                d["%s_value" % var] = i
                d["%s_index" % var] = index
                d["%s_first" % var] = index == 0
                d["%s_even" % var] = index % 2
                d["%s_odd" % var] = (index + 1) % 2
                d["%s_last" % var] = index + 1 == size
                if index % 2:
                    d["%s_parity" % var] = 'odd'
                else:
                    d["%s_parity" % var] = 'even'
                if 'as' in t_att:
                    d[var] = i
                elif isinstance(i, dict):
                    d.update(i)
                ru.append(self.render_element(e, t_att, g_att, d))
                index += 1
            return "".join(ru)
        else:
            raise NameError("QWeb: foreach enumerator %r is not defined while rendering template %r" % (expr, v.get('__template__')))

    def render_tag_if(self, e, t_att, g_att, v):
        if self.eval_bool(t_att["if"], v):
            return self.render_element(e, t_att, g_att, v)
        else:
            return ""

    def render_tag_call(self, e, t_att, g_att, v):
        d = v if 'import' in t_att else v.copy()
        d[0] = self.render_element(e, t_att, g_att, d)

        return self.render(self.eval_format(t_att["call"], d), d)

    def render_tag_set(self, e, t_att, g_att, v):
        if "value" in t_att:
            v[t_att["set"]] = self.eval_object(t_att["value"], v)
        elif "valuef" in t_att:
            v[t_att["set"]] = self.eval_format(t_att["valuef"], v)
        else:
            v[t_att["set"]] = self.render_element(e, t_att, g_att, v)
        return ""

    def render_tag_field(self, e, t_att, g_att, v):
        """ eg: <span t-record="browse_record(res.partner, 1)" t-field="phone">+1 555 555 8069</span>"""
        node_name = e.nodeName
        assert node_name not in ("table", "tbody", "thead", "tfoot", "tr", "td",
                                 "ol", "ul", "ol", "dl", "dt", "dd"),\
            "RTE widgets do not work correctly on %r elements" % node_name
        assert node_name != 't',\
            "t-field can not be used on a t element, provide an actual HTML node"

        record, field_name = t_att["field"].rsplit('.', 1)
        record = self.eval_object(record, v)

        column = record._model._all_columns[field_name].column
        options = json.loads(t_att.get('field-options') or '{}')
        field_type = get_field_type(column, options)

        converter = self.get_converter_for(field_type)

        return converter.to_html(record._cr, record._uid, field_name, record, options,
                                 e, t_att, g_att, v)

    def get_converter_for(self, field_type):
        return self.pool.get('ir.qweb.field.' + field_type,
                             self.pool['ir.qweb.field'])


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
                   source_element, g_att, t_att, qweb_context):
        """
        Generates the metadata attributes (prefixed by ``data-oe-`` for the
        root node of the field conversion. Attribute values are escaped by the
        parent using ``werkzeug.utils.escape``.

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

    def value_to_html(self, cr, uid, value, column, options=None):
        """ Converts a single value to its HTML version/output
        """
        return werkzeug.utils.escape(value)

    def record_to_html(self, cr, uid, field_name, record, column, options=None):
        """ Converts the specified field of the browse_record ``record`` to
        HTML
        """
        return self.value_to_html(
            cr, uid, record[field_name], column, options=None)

    def to_html(self, cr, uid, field_name, record, options,
                source_element, t_att, g_att, qweb_context):
        """ Converts a ``t-field`` to its HTML output. A ``t-field`` may be
        extended by a ``t-field-options``, which is a JSON-serialized mapping
        of configuration values.

        A default configuration key is ``widget`` which can override the
        field's own ``_type``.
        """
        content = None
        try:
            content = self.record_to_html(
                cr, uid, field_name, record,
                record._model._all_columns[field_name].column,
                options)
        except Exception:
            _logger.warning("Could not get field %s for model %s",
                            field_name, record._model._name, exc_info=True)

        g_att += ''.join(
            ' %s="%s"' % (name, werkzeug.utils.escape(value))
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

class FloatConverter(osv.AbstractModel):
    _name = 'ir.qweb.field.float'
    _inherit = 'ir.qweb.field'

    def value_to_html(self, cr, uid, value, column, options=None):
        width, precision = column.digits or (None, None)
        fmt = '{value}' if precision is None else '{value:.{precision}f}'

        return werkzeug.utils.escape(
            fmt.format(value=value, width=width, precision=precision, ))

class TextConverter(osv.AbstractModel):
    _name = 'ir.qweb.field.text'
    _inherit = 'ir.qweb.field'

    def value_to_html(self, cr, uid, value, column, options=None):
        """
        Escapes the value and converts newlines to br. This is bullshit.
        """
        return werkzeug.utils.escape(value).replace('\n', '<br>\n')

class SelectionConverter(osv.AbstractModel):
    _name = 'ir.qweb.field.selection'
    _inherit = 'ir.qweb.field'

    def record_to_html(self, cr, uid, field_name, record, column, options=None):
        # FIXME: context
        value = record[field_name]
        selection = dict(fields.selection.reify(
            cr, uid, record._model, column))
        return self.value_to_html(
            cr, uid, selection[value], column, options=options)

class ManyToOneConverter(osv.AbstractModel):
    _name = 'ir.qweb.field.many2one'
    _inherit = 'ir.qweb.field'

    def value_to_html(self, cr, uid, value, column, options=None):
        return werkzeug.utils.escape(value.name_get()[0][1]).replace('\n', '<br>\n')

class HTMLConverter(osv.AbstractModel):
    _name = 'ir.qweb.field.html'
    _inherit = 'ir.qweb.field'

    def value_to_html(self, cr, uid, value, column, options=None):
        return value

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

    def value_to_html(self, cr, uid, value, column, options=None):
        try:
            image = Image.open(cStringIO.StringIO(value.decode('base64')))
            image.verify()
        except IOError:
            raise ValueError("Non-image binary fields can not be converted to HTML")
        except: # image.verify() throws "suitable exceptions", I have no idea what they are
            raise ValueError("Invalid image content")

        return '<img src="data:%s;base64,%s">' % (Image.MIME[image.format], value)

class MonetaryConverter(osv.AbstractModel):
    """ ``monetary`` converter, has a mandatory option
    ``display_currency``.

    .. note:: the monetary converter internally adds the qweb context to its
              options mapping, so that the context is available to callees.
              It's set under the ``_qweb_context`` key.
    """
    _name = 'ir.qweb.field.monetary'
    _inherit = 'ir.qweb.field'

    def to_html(self, cr, uid, field_name, record, options,
                source_element, t_att, g_att, qweb_context):
        options['_qweb_context'] = qweb_context
        return super(MonetaryConverter, self).to_html(
            cr, uid, field_name, record, options,
            source_element, t_att, g_att, qweb_context)

    def record_to_html(self, cr, uid, field_name, record, column, options):
        Currency = self.pool['res.currency']
        display = self.display_currency(cr, uid, options)

        symbol_pre = symbol_post = space_pre = space_post = u''
        if display.position == 'before':
            space_pre = u' '
            symbol_pre = display.symbol
        else:
            space_post = u' '
            symbol_post = display.symbol

        return u'{symbol_pre}{space_pre}' \
               u'<span class="oe_currency_value">{0}</span>' \
               u'{space_post}{symbol_post}'.format(
            Currency.round(cr, uid, display, record[field_name]),
            space_pre=space_pre,
            symbol_pre=symbol_pre,
            space_post=space_post,
            symbol_post=symbol_post,)

    def display_currency(self, cr, uid, options):
        return self.qweb_object().eval_object(
            options['display_currency'], options['_qweb_context'])

def get_field_type(column, options):
    """ Gets a t-field's effective type from the field's column and its options
    """
    return options.get('widget', column._type)

# vim:et:
