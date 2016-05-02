# -*- coding: utf-8 -*-

import ast
from collections import OrderedDict
import json
from urlparse import urlparse
from lxml import etree, html
import re
import itertools
import textwrap
import traceback

import openerp.tools
from odoo.exceptions import QWebException

from openerp.tools import html_escape
from . import utils
from .utils import QWebContext, unicodifier
from .assetsbundle import AssetsBundle

from odoo import models

try:
    import astor
except ImportError:
    astor = None

import logging
_logger = logging.getLogger(__name__)


class QWeb(models.AbstractModel):
    """ Base QWeb rendering engine
    * to customize ``t-field`` rendering, subclass ``ir.qweb.field`` and
      create new models called :samp:`ir.qweb.field.{widget}`
    * alternatively, override :meth:`~.get_field_for` and return an
      arbitrary model to use as field converter
    Beware that if you need extensions or alterations which could be
    incompatible with other subsystems, you should create a local object
    inheriting from ``ir.qweb`` and customize that.
    """

    _name = 'ir.qweb'

    def get_template(self, name, loader, origin_template=None):
        try:
            document = loader(name)
        except ValueError:
            raise QWebException("%s\nLoader could not find template %r" % (traceback.format_exc(), name), template=origin_template)
        else:
            if document is not None:
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

        raise QWebException("%s\nTemplate %r not found" % (traceback.format_exc(), name), template=origin_template)

    def render(self, cr, uid, id_or_xml_id, qwebcontext=None, loader=None, context=None):
        """ render(cr, uid, id_or_xml_id, qwebcontext=None, loader=None, context=None)
        Renders the template specified by the provided template name
        :param qwebcontext: context for rendering the template
        :type qwebcontext: dict or :class:`QWebContext` instance
        :param loader: if ``qwebcontext`` is a dict, loader set into the
                       context instantiated for rendering
        """
        # noinspection PyMethodFirstArgAssignment
        self = self.browse(cr, uid, [], context=context)
        if qwebcontext is None:
            qwebcontext = {}

        if not isinstance(qwebcontext, QWebContext):
            qwebcontext = QWebContext(self.env, qwebcontext, loader=loader)

        qwebcontext['__template__'] = id_or_xml_id
        stack = qwebcontext.get('__stack__', [])
        if stack:
            qwebcontext['__caller__'] = stack[-1]
        stack.append(id_or_xml_id)
        qwebcontext['__stack__'] = stack
        qwebcontext['xmlid'] = str(stack[0]) # Temporary fix

        template_function = self._get_template(id_or_xml_id, qwebcontext)

        for method in dir(self):
            if method.startswith('render_'):
                _logger.warning("Method '%s' found in ir.qweb, please remove it." % method)

        return template_function(qwebcontext)

    def get_field_for(self, field_type, cr=None, uid=None, context=None):
        """ returns a :class:`~openerp.models.Model` used to render a
        ``t-field``.
        By default, tries to get the model named
        :samp:`ir.qweb.field.{field_type}`, falling back on ``ir.qweb.field``.
        :param str field_type: type or widget of field to render
        :param cursor cr
        :param int uid
        :param dict context
        """
        model = 'ir.qweb.field.' + field_type
        env = self.env(cr=cr, user=uid, context=context)
        return env[model] if model in env else env['ir.qweb.field']

    def format(value, formating, *args, **kwargs):
        format = getattr(self, '_format_func_%s' % formating, None)
        if not format:
            raise "Unknown formating '%s'" % (formating,)
        return format(value, *args, **kwargs)

    def _format_func_monetary(self, value, display_currency=None, from_currency=None):
        precision = int(round(math.log10(display_currency.rounding)))
        fmt = "%.{0}f".format(-precision if precision < 0 else 0)
        lang_code = self.env.context.get('lang') or 'en_US'
        lang = self.env['res.lang']._lang_get(lang_code)
        formatted_amount = lang.format(fmt, value, grouping=True, monetary=True)
        pre = post = u''
        if display_currency.position == 'before':
            pre = u'{symbol}\N{NO-BREAK SPACE}'
        else:
            post = u'\N{NO-BREAK SPACE}{symbol}'
        return u'{pre}{0}{post}'.format(
            formatted_amount, pre=pre, post=post
        ).format(symbol=display_currency.symbol,)


    _void_elements = frozenset([
        'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'keygen',
        'link', 'menuitem', 'meta', 'param', 'source', 'track', 'wbr'])

    _name_gen = itertools.count()

    def compile(self, element):
        xmlid = element.get('t-name', 'unknown')
        mod = utils.base_module()

        string = etree.tostring(element)

        try:
            ast_calls = self._compile_document(element)
        except Exception, e:
            raise QWebException("%s%s\nError when compiling AST" % (e, traceback.format_exc()), template=xmlid)

        mod.body.extend(ast_calls)
        ast.fix_missing_locations(mod)

        def formatException(e, message):
            if isinstance(e, QWebException):
                return e
            stack = traceback.format_exc()

            if astor:
                code = astor.to_source(mod)
            else:
                code = "Please install astor to display the compiled code"
                stack += "\nInstall `astor` for compiled source information."

            return QWebException(
                "%s%s\n%s\nTemplate: %s\nCompiled code:\n%s\nTemplate:\n%s" % (
                    e, stack, message, xmlid, code, string), template=xmlid)

        try:
            # noinspection PyBroadException
            ns = {}
            eval(compile(mod, '<template>', 'exec'), ns)
        except Exception, e:
            raise formatException(e, "Error when compiling AST")

        def _compiled_fn(qw):
            try:
                return ns[ast_calls[-1].name](self, qw)
            except Exception, e:
                raise formatException(e, "Error to render compiling AST")

        return _compiled_fn

    def _append(self, item):
        assert isinstance(item, ast.expr) or isinstance(item, ast.Expr)
        return ast.Expr(ast.Call(
            func=ast.Attribute(
                value=ast.Name(id='output', ctx=ast.Load()),
                attr='append',
                ctx=ast.Load()
            ), args=[item], keywords=[],
            starargs=None, kwargs=None
        ))

    def _extend(self, items):
        return ast.Expr(ast.Call(
            func=ast.Attribute(
                value=ast.Name(id='output', ctx=ast.Load()),
                attr='extend',
                ctx=ast.Load()
            ), args=[items], keywords=[],
            starargs=None, kwargs=None
        ))

    def _if_content_is_not_Falsy(self, body, orelse):
        return ast.If(
                # if content is not None and content is not False
                test=ast.BoolOp(
                    op=ast.And(),
                    values=[
                        ast.Compare(
                            left=ast.Name(id='content', ctx=ast.Load()),
                            ops=[ast.IsNot()],
                            comparators=[ast.Name(id='None', ctx=ast.Load())]
                        ),
                        ast.Compare(
                            left=ast.Name(id='content', ctx=ast.Load()),
                            ops=[ast.IsNot()],
                            comparators=[ast.Name(id='False', ctx=ast.Load())]
                        )
                    ]
                ),
                # output.append(escape($content))
                body=body,
                # output.append(body default value)
                orelse=orelse,
            )

    def _call_body(self, ast_calls, body, args=('self', 'qwebcontext',), prefix='fn', lineno=None):
        """
        If ``body`` is non-empty, generates (and globally store) the
        corresponding function definition and returns the relevant ast.Call
        node.
        If ``body`` is empty, doesn't do anything and returns ``None``.
        """
        if not body:
            return None
        name = self._make_name(prefix)
        ast_calls.append(utils.base_fn_def(body, name=name, lineno=lineno))
        return ast.Call(
            func=ast.Name(id=name, ctx=ast.Load()),
            args=[ast.Name(id=arg, ctx=ast.Load()) for arg in args],
            keywords=[], starargs=None, kwargs=None
        )

    def _make_name(self, prefix='var'):
        return "%s_%s" % (prefix, next(self._name_gen))

    def _compile_document(self, element):
        """
        Compiles a document rooted in ``element`` to a Python AST.
        Calls the following hooks:
        * :samp:`_compile_directive_{name}` compiles the directive of the
          specified name to AST
        In either case, the current etree._Element is received as first
        parameter and the list of ast_calls as second. A brand new list
        of AST nodes *must* be returned (can be an empty list).
        :return a list of AST nodes, the last AST node is the template call
        """
        ast_calls = []
        self._call_body(ast_calls,
            self._compile_directive_content(element, ast_calls),
            prefix='template_%s' % element.get('t-name', 'unknown').replace('.', '_'))
        return ast_calls

    def _compile_node(self, el, ast_calls):
        """
        :return ast list
        """
        ignored = self._nondirectives_ignore()

        if el.get("groups"):
            el.set("t-groups", el.attrib.pop("groups"))

        directives = {
            att[2:]
            for att in el.attrib
            if att.startswith('t-')
            if not att.startswith('t-att')
            if att not in ignored
        }

        for name in self._directives_eval_order():
            # skip directives not present on the element
            if name not in directives:
                continue
            directives.remove(name)
            mname = name.replace('-', '_')
            compile_handler = getattr(self, '_compile_directive_%s' % mname, None)
            interpret_handler = 'render_tag_%s' % mname
            if hasattr(self, interpret_handler):
                _logger.warning(
                    "Directive '%s' must be AOT-compiled. Dynamic interpreter %s will ignored",
                    name, interpret_handler
                )
            return compile_handler(el, ast_calls)
        if directives:
            raise "Unknown directive '%s' on %s" % ("', '".join(directives), etree.tostring(el))

        return []

    def _directives_eval_order(self):
        """ Should list all supported directives in the order in which they
        should evaluate when set on the same element. E.g. if a node bearing
        both ``foreach`` and ``if`` should see ``foreach`` executed before
        ``if`` aka
        .. code-block:: xml
            <el t-foreach="foo" t-as="bar" t-if="bar">
        should be equivalent to
        .. code-block:: xml
            <t t-foreach="foo" t-as="bar">
                <t t-if="bar">
                    <el>
        then this method should return ``['foreach', 'if']``
        """
        return [
            'debug',
            'groups', 'foreach', 'if',
            'call-assets',
            'field',
            'tag',
            'call',
            'set',
            'esc', 'raw', 'content',
        ]

    def _nondirectives_ignore(self):
        """
        t-* attributes existing as support for actual directives, should just
        be ignored
        :returns: set
        """
        return {
            't-name', 't-field-options', 't-as', 't-lang',
            't-value', 't-valuef', 't-ignore', 't-js', 't-css', 't-async', 't-placeholder',
        }

    def _serialize_static_attributes(self, el):
        nodes = []
        for key, value in el.attrib.iteritems():
            if not key.startswith('t-'):
                nodes.append((key, ast.Str(value)))
        return nodes

    def _compile_dynamic_attributes(self, el):
        nodes = []
        for name, value in el.attrib.iteritems():
            if name.startswith('t-attf-'):
                nodes.append((name[7:], utils.compile_format(value)))
            elif name.startswith('t-att-'):
                nodes.append((name[6:], utils.compile_expr(value)))
            elif name == 't-att':
                nodes.append(ast.Call(
                    func=ast.Attribute(
                        value=ast.Name(id='self', ctx=ast.Load()),
                        attr='_compile_dynamic_att',
                        ctx=ast.Load()
                    ),
                    args=[
                        ast.Str(el.tag),
                        utils.compile_expr(value),
                        ast.Name(id='qwebcontext', ctx=ast.Load()),
                    ], keywords=[],
                    starargs=None, kwargs=None
                ))
        return nodes

    def _compile_dynamic_att(self, tagName, atts, qwebcontext):
        if isinstance(atts, OrderedDict):
            return atts
        if isinstance(atts, (list, tuple)) and not isinstance(atts[0], (list, tuple)):
            atts = [atts]
        if isinstance(atts, (list, tuple)):
            atts = OrderedDict(atts)
        return atts

    def _compile_all_attributes(self, el, attr_already_created=False):
        body = []
        if any(name.startswith('t-att') or not name.startswith('t-') for name, value in el.attrib.iteritems()):
            if not attr_already_created:
                attr_already_created = True
                body.append(
                    ast.Assign(
                        targets=[ast.Name(id='t_attrs', ctx=ast.Store())],
                        value=ast.Call(
                            func=ast.Name(id='OrderedDict', ctx=ast.Load()),
                            args=[],
                            keywords=[], starargs=None, kwargs=None
                        )
                    )
                )

            items = self._serialize_static_attributes(el) + self._compile_dynamic_attributes(el)
            for item in items:
                if isinstance(item, tuple):
                    body.append(ast.Assign(
                        targets=[ast.Subscript(
                            value=ast.Name(id='t_attrs', ctx=ast.Load()),
                            slice=ast.Index(ast.Str(item[0])),
                            ctx=ast.Store()
                        )],
                        value=item[1]
                    ))
                elif item:
                    body.append(ast.Expr(ast.Call(
                        func=ast.Attribute(
                            value=ast.Name(id='t_attrs', ctx=ast.Load()),
                            attr='update',
                            ctx=ast.Load()
                        ),
                        args=[item],
                        keywords=[],
                        starargs=None, kwargs=None
                    )))

        if attr_already_created:
            # for name, value in t_attrs.iteritems():
            #     if value or isinstance(value, basestring)):
            #         output.append(u' ')
            #         output.append(name)
            #         output.append(u'="')
            #         output.append(escape(unicodifier(value)))
            #         output.append(u'"')
            body.append(ast.For(
                target=ast.Tuple(elts=[ast.Name(id='name', ctx=ast.Store()), ast.Name(id='value', ctx=ast.Store())], ctx=ast.Store()),
                iter=ast.Call(
                    func=ast.Attribute(
                        value=ast.Name(id='t_attrs', ctx=ast.Load()),
                        attr='iteritems',
                        ctx=ast.Load()
                        ),
                    args=[], keywords=[],
                    starargs=None, kwargs=None
                ),
                body=[ast.If(
                    test=ast.BoolOp(
                        op=ast.Or(),
                        values=[
                            ast.Name(id='value', ctx=ast.Load()),
                            ast.Call(
                                func=ast.Name(id='isinstance', ctx=ast.Load()),
                                args=[
                                    ast.Name(id='value', ctx=ast.Load()),
                                    ast.Name(id='basestring', ctx=ast.Load())
                                ],
                                keywords=[],
                                starargs=None, kwargs=None
                            )
                        ]
                    ),
                    body=[
                        self._append(ast.Str(u' ')),
                        self._append(ast.Name(id='name', ctx=ast.Load())),
                        self._append(ast.Str(u'="')),
                        self._append(ast.Call(
                            func=ast.Name(id='escape', ctx=ast.Load()),
                            args=[
                                ast.Call(
                                    func=ast.Name(id='unicodifier', ctx=ast.Load()),
                                    args=[ast.Name(id='value', ctx=ast.Load())], keywords=[],
                                    starargs=None, kwargs=None
                                )
                            ], keywords=[],
                            starargs=None, kwargs=None
                        )),
                        self._append(ast.Str(u'"')),
                    ],
                    orelse=[]
                )],
                orelse=[]
            ))

        return body

    def _compile_tag(self, el, content, attr_already_created=False):
        body = [self._append(ast.Str(u'<%s' % el.tag))]
        body.extend(self._compile_all_attributes(el, attr_already_created))
        if el.tag in self._void_elements:
            body.append(self._append(ast.Str(u'/>')))
            body.extend(content)
        else:
            body.append(self._append(ast.Str(u'>')))
            body.extend(content)
            body.append(self._append(ast.Str(u'</%s>' % el.tag)))
        return body

    def _compile_directive_debug(self, el, ast_calls):
        debugger = el.attrib.pop('t-debug')
        body = self._compile_node(el, ast_calls)
        if 'qweb' in openerp.tools.config['dev_mode']:
            body = ast.parse("__import__('%s').set_trace()" % re.sub('[^a-zA-Z]', '', debugger)).body + body  # pdb, ipdb, pudb, ...
        else:
            _logger.warning("@t-debug in template is only available in --dev mode")
        return body

    def _compile_directive_tag(self, el, ast_calls):
        el.attrib.pop('t-tag', None)
        content = self._compile_node(el, ast_calls)
        if el.tag == 't':
            return content
        return self._compile_tag(el, content, False)

    def _compile_directive_set(self, el, ast_calls):
        if 't-value' in el.attrib:
            value = utils.compile_expr(el.attrib.pop('t-value'))
        elif 't-valuef' in el.attrib:
            value = utils.compile_format(el.attrib.pop('t-valuef'))
        else:
            render = self._call_body(ast_calls, self._compile_directive_content(el, ast_calls), prefix='set', lineno=el.sourceline)
            if render is None:
                value = ast.Str(u'')
            else:
                # concat body render to string
                value = ast.Call(
                    func=ast.Attribute(value=ast.Str(u''), attr='join', ctx=ast.Load()),
                    args=[render], keywords=[],
                    starargs=None, kwargs=None
                )

        return [
            ast.Assign(
                targets=[ast.Subscript(
                    value=ast.Name(id='qwebcontext', ctx=ast.Load()),
                    slice=ast.Index(ast.Str(el.attrib.pop('t-set'))),
                    ctx=ast.Store()
                )],
                value=value
            )]

    def _compile_directive_esc(self, el, ast_calls):
        return [
            # content = t-raw value
            ast.Assign(
                targets=[ast.Name(id='content', ctx=ast.Store())],
                value=utils.compile_expr0(el.attrib.pop('t-esc')),
            ),
            # if content is not None: display
            self._if_content_is_not_Falsy(
                # output.append(escape($content))
                body=[self._append(ast.Call(
                    func=ast.Name(id='escape', ctx=ast.Load()),
                    args=[ast.Call(
                        func=ast.Name(id='unicodifier', ctx=ast.Load()),
                        args=[ast.Name(id='content', ctx=ast.Load())], keywords=[],
                        starargs=None, kwargs=None
                    )],
                    keywords=[], starargs=None, kwargs=None
                ))],
                # output.append(body default value)
                orelse=self._compile_directive_content(el, ast_calls),
            )
        ]

    def _compile_directive_raw(self, el, ast_calls):
        return [
            # content = t-raw value
            ast.Assign(
                targets=[ast.Name(id='content', ctx=ast.Store())],
                value=utils.compile_expr0(el.attrib.pop('t-raw')),
            ),
            self._if_content_is_not_Falsy(
                # output.append($content)
                body=[self._append(ast.Call(
                    func=ast.Name(id='unicodifier', ctx=ast.Load()),
                    args=[ast.Name(id='content', ctx=ast.Load())], keywords=[],
                    starargs=None, kwargs=None
                ))],
                # output.append(body default value)
                orelse=self._compile_directive_content(el, ast_calls),
            )
        ]

    def _compile_directive_content(self, el, ast_calls):
        body = []
        if el.text is not None:
            body.append(self._append(ast.Str(unicodifier(el.text))))
        if el.getchildren():
            for item in el:
                # ignore comments & processing instructions
                if isinstance(item, etree._Comment):
                    continue
                item.set('t-tag', item.tag)
                if not (set(['t-esc', 't-raw', 't-field']) & set(item.attrib)):
                    item.set('t-content', 'True')
                body.extend(self._compile_node(item, ast_calls))
                body.extend(self._compile_tail(item))
        return body

    def _compile_directive_call(self, el, ast_calls):
        """
        :param etree._Element el:
        :param list ast call:
        :return: new body
        :rtype: list(ast.AST)
        """
        tmpl = el.attrib.pop('t-call')
        qw = self._make_name('qwebcontext_copy')
        sub_content = self._call_body(ast_calls, self._compile_directive_content(el, ast_calls),
            prefix='body_call_content', args=('self', qw,), lineno=el.sourceline)
        lang = el.get('t-lang', "'en_US'")

        content = [
            # qwebcontext_copy = qwebcontext.copy()
            ast.Assign(
                targets=[ast.Name(id=qw, ctx=ast.Store())],
                value=ast.Call(
                    func=ast.Attribute(
                        value=ast.Name(id='qwebcontext', ctx=ast.Load()),
                        attr='copy',
                        ctx=ast.Load()
                    ),
                    args=[], keywords=[],
                    starargs=None, kwargs=None
                )
            )
        ]

        qw_0_ast = ast.Subscript(
            value=ast.Name(id=qw, ctx=ast.Load()),
            slice=ast.Index(ast.Num(0)),
            ctx=ast.Store()
        )

        # qwebcontext_copy[0] = body_call_content or u''
        content.append(
            ast.Assign(
                targets=[qw_0_ast],
                value=sub_content or ast.Str(u'')
            ))

        # qwebcontext_copy.env = qwebcontext.env(context=dict(qwebcontext.env.context, lang=$lang))
        if lang:
            content.append(
                ast.Assign(
                    targets=[ast.Attribute(
                        value=ast.Name(id=qw, ctx=ast.Load()),
                        attr='env',
                        ctx=ast.Store()
                    )],
                    value=ast.Call(
                        func=ast.Attribute(
                            value=ast.Name(id='qwebcontext', ctx=ast.Load()),
                            attr='env',
                            ctx=ast.Load()
                        ),
                        args=[],
                        keywords=[ast.keyword('context', ast.Call(
                            func=ast.Name(id='dict', ctx=ast.Load()),
                            args=[ast.Attribute(
                                value=ast.Attribute(
                                    value=ast.Name(id='qwebcontext', ctx=ast.Load()),
                                    attr='env',
                                    ctx=ast.Load()
                                ),
                                attr='context',
                                ctx=ast.Load()
                            )],
                            keywords=[ast.keyword('lang', utils.compile_strexpr(lang))],
                            starargs=None, kwargs=None
                        ))],
                        starargs=None, kwargs=None
                    )
                ))

            # qwebcontext.env['ir.qweb']
            compute_self = ast.Subscript(
                value=ast.Attribute(
                    value=ast.Name(id=qw, ctx=ast.Load()),
                    attr='env',
                    ctx=ast.Load()
                ),
                slice=ast.Index(ast.Str('ir.qweb')),
                ctx=ast.Load()
            )
        else:
            compute_self = ast.Name(id='self', ctx=ast.Load())

        # ouput.append(self._get_template($tmpl, qwebcontext)(self, qwebcontext_copy))
        content.append(
            self._append(
                ast.Call(
                    func=ast.Call(
                        func=ast.Attribute(
                            value=compute_self,
                            attr='_get_template',
                            ctx=ast.Load()
                        ),
                        args=[
                            ast.Str(str(tmpl)),
                            ast.Name(id=qw, ctx=ast.Load()),
                        ],
                        keywords=[], starargs=None, kwargs=None
                    ),
                    args=[ast.Name(id=qw, ctx=ast.Load())],
                    keywords=[], starargs=None, kwargs=None
                )
            ))
        return content

    def _compile_directive_if(self, el, ast_calls):
        orelse = []
        if el.tail and re.search(r'\S', el.tail):
            next = el.getnext()
            if next is not None and 't-else' in next.attrib:
                el.tail = None
                next.attrib.pop('t-else')
                orelse = self._compile_node(next, ast_calls)
                next.getparent().remove(next)
        return [
            ast.If(
                test=utils.compile_expr(el.attrib.pop('t-if')),
                body=self._compile_node(el, ast_calls),
                orelse=orelse
            )
        ]

    def _compile_directive_groups(self, el, ast_calls):
        return [
            ast.If(
                test=ast.Call(
                    func=ast.Attribute(
                        value=ast.Name(id='self', ctx=ast.Load()),
                        attr='user_has_groups',
                        ctx=ast.Load()
                    ),
                    args=[ast.Str(el.attrib.pop('t-groups'))], keywords=[],
                    starargs=None, kwargs=None
                ),
                body=self._compile_node(el, ast_calls),
                orelse=[]
            )
        ]

    def _compile_directive_foreach(self, el, ast_calls):
        expr = utils.compile_expr(el.attrib.pop('t-foreach'))
        varname = el.attrib.pop('t-as').replace('.', '_')

        # foreach_iterator(qwebcontext, <expr>, varname)
        it = ast.Call(
            func=ast.Name(id='foreach_iterator', ctx=ast.Load()),
            args=[ast.Name(id='qwebcontext', ctx=ast.Load()), expr, ast.Str(varname)],
            keywords=[], starargs=None, kwargs=None
        )
        # itertools.repeat(self)
        selfs = ast.Call(
            func=ast.Attribute(
                value=ast.Name(id='itertools', ctx=ast.Load()),
                attr='repeat',
                ctx=ast.Load()
            ), args=[ast.Name(id='self', ctx=ast.Load())], keywords=[],
            starargs=None, kwargs=None
        )

        # create function $foreach
        call = self._call_body(ast_calls, self._compile_node(el, ast_calls), prefix='foreach', lineno=el.sourceline)

        # itertools.imap($foreach(), repeat(self), it)
        it = ast.Call(
            func=ast.Attribute(
                value=ast.Name(id='itertools', ctx=ast.Load()),
                attr='imap',
                ctx=ast.Load()
            ), args=[call.func, selfs, it], keywords=[],
            starargs=None, kwargs=None
        )
        # itertools.chain.from_iterable(previous)
        it = ast.Call(
            func=ast.Attribute(
                value=ast.Attribute(
                    value=ast.Name(id='itertools', ctx=ast.Load()),
                    attr='chain',
                    ctx=ast.Load()
                ),
                attr='from_iterable',
                ctx=ast.Load()
            ), args=[it], keywords=[],
            starargs=None, kwargs=None
        )
        return [self._extend(it)]

    def _compile_tail(self, el):
        return el.tail is not None and [self._append(ast.Str(unicodifier(el.tail)))] or []

    def _compile_directive_call_assets(self, el, ast_calls):
        """ This special 't-call' tag can be used in order to aggregate/minify javascript and css assets"""
        if len(el):
            raise "t-call-assets cannot contain children nodes"

        # self._get_asset(xmlid, qwebcontext).to_html(css, js, debug, asunc qwebcontext)
        return [
            self._append(ast.Call(
                func=ast.Attribute(
                    value=ast.Call(
                        func=ast.Attribute(
                            value=ast.Name(id='self', ctx=ast.Load()),
                            attr='_get_asset',
                            ctx=ast.Load()
                        ),
                        args=[
                            ast.Str(el.get('t-call-assets')),
                            ast.Name(id='qwebcontext', ctx=ast.Load()),
                        ],
                        keywords=[], starargs=None, kwargs=None
                    ),
                    attr='to_html',
                    ctx=ast.Load()
                ),
                args=[],
                keywords=[
                    ast.keyword('css', utils.get_attr_bool(el.get('t-css', True))),
                    ast.keyword('js', utils.get_attr_bool(el.get('t-js', True))),
                    ast.keyword('debug', ast.Call(
                        func=ast.Attribute(
                            value=ast.Name(id='qwebcontext', ctx=ast.Load()),
                            attr='get',
                            ctx=ast.Load()
                        ),
                        args=[ast.Str('debug')],
                        keywords=[], starargs=None, kwargs=None
                    )),
                    ast.keyword('async', utils.get_attr_bool(el.get('async', False))),
                    ast.keyword('qwebcontext', ast.Name(id='qwebcontext', ctx=ast.Load())),
                ],
                starargs=None, kwargs=None
            ))
        ]

    def _compile_directive_field(self, el, ast_calls):
        """ eg: <span t-record="browse_record(res.partner, 1)" t-field="phone">+1 555 555 8069</span>"""
        node_name = el.tag
        assert node_name not in ("table", "tbody", "thead", "tfoot", "tr", "td",
                                 "li", "ul", "ol", "dl", "dt", "dd"),\
            "RTE widgets do not work correctly on %r elements" % node_name
        assert node_name != 't',\
            "t-field can not be used on a t element, provide an actual HTML node"
        assert "." in el.get('t-field'),\
            "t-field must have at least a dot like 'record.field_name'"

        expression = el.attrib.pop('t-field')
        options = el.attrib.pop('t-field-options', None)
        record, field_name = expression.rsplit('.', 1)

        return [
            # record
            ast.Assign(
                targets=[ast.Name(id='record', ctx=ast.Store())],
                value=utils.compile_expr(record)
            ),
            # default_content = u''.join($body_content())
            ast.Assign(
                targets=[ast.Name(id='default_content', ctx=ast.Store())],
                value=self._call_body(ast_calls, self._compile_node(el, ast_calls), prefix='body_content', lineno=el.sourceline)
            ),
            # t_attrs, content = self._get_field(record, field_name, expression, options, qwebcontext)
            ast.Assign(
                targets=[ast.Tuple(elts=[ast.Name(id='t_attrs', ctx=ast.Store()), ast.Name(id='content', ctx=ast.Store())], ctx=ast.Store())],
                value=ast.Call(
                    func=ast.Attribute(
                        value=ast.Name(id='self', ctx=ast.Load()),
                        attr='_get_field',
                        ctx=ast.Load()
                    ),
                    args=[
                        ast.Name(id='record', ctx=ast.Load()),
                        ast.Str(field_name),
                        ast.Str(expression),
                        ast.Name(id='default_content', ctx=ast.Load()),
                        ast.Str(node_name),
                        options and utils.compile_format(options) or ast.Name(id='None', ctx=ast.Load()),
                        ast.Name(id='qwebcontext', ctx=ast.Load()),
                    ],
                    keywords=[], starargs=None, kwargs=None
                ),
            ),

            # if content is not None: display the tag
            self._if_content_is_not_Falsy(
                body=self._compile_tag(el, [self._append(ast.Name(id='content', ctx=ast.Load()))], True),
                orelse=[]
            )
        ]

    # assume cache will be invalidated by third party on write to ir.ui.view
    def _get_template_cache_keys(self):
        """ Return the list of context keys to use for caching ``_get_template``. """
        return ['lang', 'inherit_branding', 'editable', 'translatable', 'edit_translations']

    # apply ormcache_context decorator unless in dev mode...
    @openerp.tools.conditional(
        'xml' not in openerp.tools.config['dev_mode'],
        openerp.tools.ormcache('xmlid', 'tuple(map(self._context.get, self._get_template_cache_keys()))'),
    )
    def _get_template(self, xmlid, qwebcontext):
        element = self.get_template(xmlid, qwebcontext.loader, origin_template=qwebcontext.get('__caller__') or qwebcontext.get('__stack__', [xmlid])[0])
        element.attrib.pop("name", False)
        return self.compile(element)

    def _get_asset(self, xmlid, qwebcontext):
        files, remains = self._get_asset_content(xmlid, qwebcontext)
        return AssetsBundle(xmlid, files, remains, env=qwebcontext.env)

    @openerp.tools.ormcache('xmlid', 'qwebcontext.env.lang')
    def _get_asset_content(self, xmlid, qwebcontext):
        context = dict(self.env.context if qwebcontext is None else qwebcontext.env.context,
            inherit_branding=False, inherit_branding_auto=False,
            edit_translations=False, translatable=False,
            rendering_bundle=True)

        env = self.env(context=context)
        if qwebcontext is None:
            qwebcontext = QWebContext(env, {})
        else:
            qwebcontext = qwebcontext.copy()
            qwebcontext.env = env

        template = env['ir.qweb']._get_template(xmlid, qwebcontext)(qwebcontext)

        files = []
        remains = []
        for el in html.fragments_fromstring(template):
            if isinstance(el, basestring):
                remains.append(el)
            elif isinstance(el, html.HtmlElement):
                href = el.get('href', '')
                atype = el.get('type')
                media = el.get('media')

                can_aggregate = not urlparse(href).netloc and not href.startswith('/web/content')
                if el.tag == 'style' or (el.tag == 'link' and el.get('rel') == 'stylesheet' and can_aggregate):
                    if href.endswith('.sass'):
                        atype = 'text/sass'
                    elif href.endswith('.less'):
                        atype = 'text/less'
                    if atype not in ('text/less', 'text/sass'):
                        atype = 'text/css'
                    files.append({'atype': atype, 'url': href, 'content': el.text, 'media': media})
                elif el.tag == 'script':
                    atype = 'text/javascript'
                    files.append({'atype': atype, 'url': el.get('src', ''), 'content': el.text, 'media': media})
                else:
                    remains.append(html.tostring(el))
            else:
                try:
                    remains.append(html.tostring(el))
                except Exception:
                    # notYETimplementederror
                    raise NotImplementedError

        return (files, remains)

    def _get_field(self, record, field_name, expression, default_content, tagName, options, qwebcontext):
        options = options and json.loads(options) or {}
        field = record._fields[field_name]

        field_type = options.get('widget', field.type)

        inherit_branding = self._context.get('inherit_branding', self._context.get('inherit_branding_auto') and record.check_access_rights('write', False))
        translate = self._context.get('edit_translations') and self._context.get('translatable') and getattr(field, 'translate', False)

        options['tagName'] = tagName
        options['type'] = field_type
        options['expression'] = expression
        options['default_content'] = default_content
        options['inherit_branding'] = inherit_branding
        options['translate'] = translate

        converter = self.get_field_for(field_type, qwebcontext.cr, qwebcontext.uid, qwebcontext.context)

        content = converter.record_to_html(record, field_name, options, qwebcontext)
        attributes = converter.attributes(record, field_name, options, qwebcontext)

        return (attributes, content or default_content or (u"" if inherit_branding or translate else None))
