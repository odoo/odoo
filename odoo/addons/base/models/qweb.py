# -*- coding: utf-8 -*-
import ast
import logging
import os.path
import re
import traceback
from collections import OrderedDict
from collections.abc import Sized, Mapping
from functools import reduce
from itertools import tee, count
from textwrap import dedent
from time import time

import itertools
from lxml import etree, html
from psycopg2.extensions import TransactionRollbackError
import werkzeug
from werkzeug.utils import escape as _escape

from odoo.tools import pycompat, freehash
from odoo.tools.safe_eval import check_values

import builtins
builtin_defaults = {name: getattr(builtins, name) for name in dir(builtins)}

try:
    import astor
except ImportError:
    astor = None

from odoo.tools.parse_version import parse_version

unsafe_eval = eval

_logger = logging.getLogger(__name__)

####################################
###          qweb tools          ###
####################################


class Contextifier(ast.NodeTransformer):
    """ For user-provided template expressions, replaces any ``name`` by
    :sampe:`values.get('{name}')` so all variable accesses are
    performed on the values rather than in the "native" values
    """

    # some people apparently put lambdas in template expressions. Turns out
    # the AST -> bytecode compiler does *not* appreciate parameters of lambdas
    # being converted from names to subscript expressions, and most likely the
    # reference to those parameters inside the lambda's body should probably
    # remain as-is. Because we're transforming an AST, the structure should
    # be lexical, so just store a set of "safe" parameter names and recurse
    # through the lambda using a new NodeTransformer
    def __init__(self, params=()):
        super(Contextifier, self).__init__()
        self._safe_names = tuple(params)

    def visit_Name(self, node):
        if node.id in self._safe_names:
            return node

        return ast.copy_location(
            # values.get(name)
            ast.Call(
                func=ast.Attribute(
                    value=ast.Name(id='values', ctx=ast.Load()),
                    attr='get',
                    ctx=ast.Load()
                ),
                args=[ast.Str(node.id)], keywords=[],
                starargs=None, kwargs=None
            ),
            node
        )

    def visit_Lambda(self, node):
        args = node.args
        # assume we don't have any tuple parameter, just names
        names = [arg.arg for arg in args.args]
        if args.vararg: names.append(args.vararg)
        if args.kwarg: names.append(args.kwarg)
        # remap defaults in case there's any
        return ast.copy_location(ast.Lambda(
            args=ast.arguments(
                args=args.args,
                defaults=[self.visit(default) for default in args.defaults],
                vararg=args.vararg,
                kwarg=args.kwarg,
                # assume we don't have any, not sure it's even possible to
                # handle that cross-version
                kwonlyargs=[],
                kw_defaults=[],
                posonlyargs=[],
            ),
            body=Contextifier(self._safe_names + tuple(names)).visit(node.body)
        ), node)

    # "lambda problem" also exists with comprehensions
    def _visit_comp(self, node):
        # CompExp(?, comprehension* generators)
        # comprehension = (expr target, expr iter, expr* ifs)

        # collect names in generators.target
        names = tuple(
            node.id
            for gen in node.generators
            for node in ast.walk(gen.target)
            if isinstance(node, ast.Name)
        )
        transformer = Contextifier(self._safe_names + names)
        # copy node
        newnode = ast.copy_location(type(node)(), node)
        # then visit the comp ignoring those names, transformation is
        # probably expensive but shouldn't be many comprehensions
        for field, value in ast.iter_fields(node):
            # map transformation of comprehensions
            if isinstance(value, list):
                setattr(newnode, field, [transformer.visit(v) for v in value])
            else: # set transformation of key/value/expr fields
                setattr(newnode, field, transformer.visit(value))
        return newnode
    visit_GeneratorExp = visit_ListComp = visit_SetComp = visit_DictComp = _visit_comp


class QWebException(Exception):
    def __init__(self, message, error=None, path=None, html=None, name=None, astmod=None):
        self.error = error
        self.message = message
        self.path = path
        self.html = html
        self.name = name
        self.stack = traceback.format_exc()
        if astmod:
            if astor:
                self.code = astor.to_source(astmod)
            else:
                self.code = "Please install astor to display the compiled code"
                self.stack += "\nInstall `astor` for compiled source information."
        else:
            self.code = None

        if self.error:
            self.message = "%s\n%s: %s" % (self.message, self.error.__class__.__name__, self.error)
        if self.name:
            self.message = "%s\nTemplate: %s" % (self.message, self.name)
        if self.path:
            self.message = "%s\nPath: %s" % (self.message, self.path)
        if self.html:
            self.message = "%s\nNode: %s" % (self.message, self.html)

        super(QWebException, self).__init__(message)

    def __str__(self):
        message = "%s\n%s\n%s" % (self.error, self.stack, self.message)
        if self.code:
            message = "%s\nCompiled code:\n%s" % (message, self.code)
        return message

    def __repr__(self):
        return str(self)

# Avoid DeprecationWarning while still remaining compatible with werkzeug pre-0.9
escape = (lambda text: _escape(text, quote=True)) if parse_version(getattr(werkzeug, '__version__', '0.0')) < parse_version('0.9.0') else _escape

def foreach_iterator(base_ctx, enum, name):
    ctx = base_ctx.copy()
    if not enum:
        return
    if isinstance(enum, int):
        enum = range(enum)
    size = None
    if isinstance(enum, Sized):
        ctx["%s_size" % name] = size = len(enum)
    if isinstance(enum, Mapping):
        enum = enum.items()
    else:
        enum = zip(*tee(enum))
    value_key = '%s_value' % name
    index_key = '%s_index' % name
    first_key = '%s_first' % name
    last_key = '%s_last' % name
    parity_key = '%s_parity' % name
    even_key = '%s_even' % name
    odd_key = '%s_odd' % name
    for index, (item, value) in enumerate(enum):
        ctx[name] = item
        ctx[value_key] = value
        ctx[index_key] = index
        ctx[first_key] = index == 0
        if size is not None:
            ctx[last_key] = index + 1 == size
        if index % 2:
            ctx[parity_key] = 'odd'
            ctx[even_key] = False
            ctx[odd_key] = True
        else:
            ctx[parity_key] = 'even'
            ctx[even_key] = True
            ctx[odd_key] = False
        yield ctx
    # copy changed items back into source context (?)
    # FIXME: maybe values could provide a ChainMap-style clone?
    for k in list(base_ctx):
        base_ctx[k] = ctx[k]

_FORMAT_REGEX = re.compile(
    # ( ruby-style )|(  jinja-style  )
    r'(?:#\{(.+?)\})|(?:\{\{(.+?)\}\})')


class frozendict(dict):
    """ An implementation of an immutable dictionary. """
    def __delitem__(self, key):
        raise NotImplementedError("'__delitem__' not supported on frozendict")
    def __setitem__(self, key, val):
        raise NotImplementedError("'__setitem__' not supported on frozendict")
    def clear(self):
        raise NotImplementedError("'clear' not supported on frozendict")
    def pop(self, key, default=None):
        raise NotImplementedError("'pop' not supported on frozendict")
    def popitem(self):
        raise NotImplementedError("'popitem' not supported on frozendict")
    def setdefault(self, key, default=None):
        raise NotImplementedError("'setdefault' not supported on frozendict")
    def update(self, *args, **kwargs):
        raise NotImplementedError("'update' not supported on frozendict")
    def __hash__(self):
        return hash(frozenset((key, freehash(val)) for key, val in self.items()))


####################################
###             QWeb             ###
####################################


class QWeb(object):
    _empty_line = re.compile(r'\n\s*\n')
    __slots__ = ()

    _void_elements = frozenset([
        'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'keygen',
        'link', 'menuitem', 'meta', 'param', 'source', 'track', 'wbr'])
    _name_gen = count()

    def _render(self, template, values=None, **options):
        """ render(template, values, **options)

        Render the template specified by the given name.

        :param template: template identifier
        :param dict values: template values to be used for rendering
        :param options: used to compile the template (the dict available for the rendering is frozen)
            * ``load`` (function) overrides the load method (returns: (template, ref))
            * ``profile`` (boolean) profile the rendering
        """

        print('')
        t = time()
        _compiled_fn = self.compile(template, options)
        print('render compile: ', (time() - t) * 1000)
        t = time()

        body = []
        _compiled_fn(self, body.append, values)

        print('render render: ', (time() - t) * 1000)
        t = time()

        l = list(body)

        print('render list: ', (time() - t) * 1000, '  number: ', len(l))
        t = time()

        joined = u''.join(l)

        print('render join: ', (time() - t) * 1000)
        t = time()

        if not values.get('__keep_empty_lines'):
            joined = QWeb._empty_line.sub('\n', joined.strip())

        print('render space: ', (time() - t) * 1000)
        t = time()

        html = joined.encode('utf8')

        print('render encode: ', (time() - t) * 1000)
        t = time()

        return html

    def compile(self, template, options):
        """ Compile the given template into a rendering function::

            render(qweb, append, values)

        where ``qweb`` is a QWeb instance, ``append`` is a unary function to
        collect strings into a result, and ``values`` are the values to render.
        """
        if options is None:
            options = {}

        _options = dict(options)
        options = frozendict(options)

        element, document, ref = self.get_template(template, options)
        if not ref:
            ref = element.get('t-name', str(document))

        _options['template'] = template
        _options['document'] = str(document, 'utf-8')
        _options['ref'] = ref
        _options['ast_calls'] = []
        _options['root'] = element.getroottree()
        _options['last_path_node'] = None
        if not options.get('nsmap'):
            _options['nsmap'] = {}

        # generate ast

        astmod = self._base_module()
        try:
            body = self._compile_start_profiling(None, None, _options) + \
                self._compile_node(element, _options) + \
                self._compile_stop_profiling(None, None, _options)
            ast_calls = _options['ast_calls']
            _options['ast_calls'] = []
            def_name = self._create_def(_options, body, prefix='template_%s' % str(ref).replace('.', '_'))
            _options['ast_calls'] += ast_calls
        except QWebException as e:
            raise e
        except Exception as e:
            path = _options['last_path_node']
            element = self.get_template(template, options)[0]
            node = element.getroottree().xpath(path) if ':' not in path else None
            raise QWebException("Error when compiling AST", e, path, node and etree.tostring(node[0], encoding='unicode'), str(ref))
        astmod.body.extend(_options['ast_calls'])
        ast.fix_missing_locations(astmod)

        # compile ast

        try:
            # noinspection PyBroadException
            ns = {}
            unsafe_eval(compile(astmod, '<template>', 'exec'), ns)
            compiled = ns[def_name]
        except QWebException as e:
            raise e
        except Exception as e:
            path = _options['last_path_node']
            element = self.get_template(template, options)[0]
            node = element.getroottree().xpath(path)
            raise QWebException("Error when compiling AST", e, path, node and etree.tostring(node[0], encoding='unicode'), str(ref))

        # return the wrapped function

        def _compiled_fn(self, append, values):
            log = {'last_path_node': ''}
            new = self.default_values()
            new.update(values)
            check_values(new)
            try:
                return compiled(self, append, new, options, log)
            except (QWebException, TransactionRollbackError) as e:
                raise e
            except Exception as e:
                path = log['last_path_node']
                element = self.get_template(template, options)[0]
                node = None
                if ':' not in path:
                    node = element.getroottree().xpath(path)
                raise QWebException("Error to render compiling AST", e, path, node and etree.tostring(node[0], encoding='unicode'), ref)

        return _compiled_fn

    def default_values(self):
        """ Return attributes added to the values for each computed template. """
        return {'format': self.format}

    def get_template(self, template, options):
        """ Retrieve the given template, and return it as a pair ``(element,
        document)``, where ``element`` is an etree, and ``document`` is the
        string document that contains ``element``.
        """
        ref = template
        if isinstance(template, etree._Element):
            element = template
            document = etree.tostring(template)
            return (element, document, template.get('t-name'))
        else:
            try:
                document, ref = options.get('load', self._load)(template, options)
            except QWebException as e:
                raise e
            except Exception as e:
                template = options.get('caller_template', template)
                path = options.get('last_path_node')
                raise QWebException("load could not load template", e, path, name=template)

        if document is None:
            raise QWebException("Template not found", name=template)

        if isinstance(document, etree._Element):
            element = document
            document = etree.tostring(document, encoding='utf-8')
        elif not document.strip().startswith('<') and os.path.exists(document):
            element = etree.parse(document).getroot()
        else:
            element = etree.fromstring(document)

        for node in element:
            if node.get('t-name') == str(template):
                return (node, document, ref)
        return (element, document, ref)

    def _load(self, template, options):
        """ Load a given template. """
        return (template, None)

    # public method for template dynamic values

    def format(self, value, formating, *args, **kwargs):
        format = getattr(self, '_format_func_%s' % formating, None)
        if not format:
            raise ValueError("Unknown format '%s'" % (formating,))
        return format(value, *args, **kwargs)

    # compute helpers

    def _base_module(self):
        """ Base module supporting qweb template functions (provides basic
        imports and utilities), returned as a Python AST.
        Currently provides:
        * collections
        * itertools
        Define:
        * escape
        * to_text (empty string for a None or False, otherwise unicode string)
        """
        return ast.parse(dedent("""
            from collections import OrderedDict
            from odoo.tools.pycompat import to_text
            from odoo.addons.base.models.qweb import escape, foreach_iterator
            """))

    def _create_def(self, options, body, prefix='fn', lineno=None):
        """ Generate (and globally store) a rendering function definition AST
        and return its name. The function takes parameters ``self``, ``append``,
        ``values``, ``options``, and ``log``. If ``body`` is empty, the function
        simply returns ``None``.
        """
        #assert body, "To create a compiled function 'body' ast list can't be empty"

        name = self._make_name(prefix)

        # def $name(self, append, values, options, log)
        fn = ast.FunctionDef(
            name=name,
            args=ast.arguments(args=[
                ast.arg(arg='self', annotation=None),
                ast.arg(arg='append', annotation=None),
                ast.arg(arg='values', annotation=None),
                ast.arg(arg='options', annotation=None),
                ast.arg(arg='log', annotation=None),
            ], defaults=[], vararg=None, kwarg=None, posonlyargs=[], kwonlyargs=[], kw_defaults=[]),
            body=body or [ast.Return()],
            decorator_list=[])
        if lineno is not None:
            fn.lineno = lineno

        options['ast_calls'].append(fn)

        return name

    def _call_def(self, name, append='append', values='values'):
        # $name(self, append, values, options, log)
        return ast.Call(
            func=ast.Name(id=name, ctx=ast.Load()),
            args=[
                ast.Name(id='self', ctx=ast.Load()),
                ast.Name(id=append, ctx=ast.Load()) if isinstance(append, str) else append,
                ast.Name(id=values, ctx=ast.Load()),
                ast.Name(id='options', ctx=ast.Load()),
                ast.Name(id='log', ctx=ast.Load()),
            ],
            keywords=[], starargs=None, kwargs=None
        )

    def _append(self, item):
        assert isinstance(item, ast.expr)
        # append(ast item)
        return ast.Expr(ast.Call(
            func=ast.Name(id='append', ctx=ast.Load()),
            args=[item], keywords=[],
            starargs=None, kwargs=None
        ))

    def _extend(self, items):
        # for x in iterator:
        #     append(x)
        var = self._make_name()
        return ast.For(
            target=ast.Name(id=var, ctx=ast.Store()),
            iter=items,
            body=[ast.Expr(ast.Call(
                func=ast.Name(id='append', ctx=ast.Load()),
                args=[ast.Name(id=var, ctx=ast.Load())], keywords=[],
                starargs=None, kwargs=None
            ))],
            orelse=[]
        )

    def _if_content_is_not_Falsy(self, body, orelse):
        return ast.If(
                # if content is not None and content is not False
                test=ast.BoolOp(
                    op=ast.And(),
                    values=[
                        ast.Compare(
                            left=ast.Name(id='content', ctx=ast.Load()),
                            ops=[ast.IsNot()],
                            comparators=[ast.Constant(None)]
                        ),
                        ast.Compare(
                            left=ast.Name(id='content', ctx=ast.Load()),
                            ops=[ast.IsNot()],
                            comparators=[ast.Constant(False)]
                        )
                    ]
                ),
                # append(escape($content))
                body=body or [ast.Pass()],
                # append(body default value)
                orelse=orelse,
            )

    def _make_name(self, prefix='var'):
        return "%s_%s" % (prefix, next(self._name_gen))

    def _compile_node(self, el, options):
        """ Compile the given element.

        :return: list of AST nodes
        """
        path = options['root'].getpath(el)
        if options['last_path_node'] != path:
            options['last_path_node'] = path
            # options['last_path_node'] = $path
            body = [ast.Assign(
                targets=[ast.Subscript(
                    value=ast.Name(id='log', ctx=ast.Load()),
                    slice=ast.Index(ast.Str('last_path_node')),
                    ctx=ast.Store())],
                value=ast.Str(path)
            )]
        else:
            body = []

        if el.get("groups"):
            el.set("t-groups", el.attrib.pop("groups"))

        # if tag don't have qweb attributes don't use directives
        if self._is_static_node(el, options):
            return self._compile_static_node(el, options)

        # create an iterator on directives to compile in order
        options['iter_directives'] = iter(self._directives_eval_order() + [None])

        el.set('t-tag', el.tag)
        if not (set(['t-esc', 't-raw', 't-field']) & set(el.attrib)):
            el.set('t-content', 'True')

        return body + self._compile_directives(el, options)

    def _compile_directives(self, el, options):
        """ Compile the given element, following the directives given in the
        iterator ``options['iter_directives']``.

        :return: list of AST nodes
        """
        # compile the first directive present on the element
        for directive in options['iter_directives']:
            if ('t-' + directive) in el.attrib:
                mname = directive.replace('-', '_')
                compile_handler = getattr(self, '_compile_directive_%s' % mname, None)

                interpret_handler = 'render_tag_%s' % mname
                if hasattr(self, interpret_handler):
                    _logger.warning(
                        "Directive '%s' must be AST-compiled. Dynamic interpreter %s will ignored",
                        mname, interpret_handler
                    )

                return compile_handler(el, options)

        # all directives have been compiled, there should be none left
        if any(att.startswith('t-') for att in el.attrib):
            raise NameError("Unknown directive on %s" % etree.tostring(el, encoding='unicode'))
        return []

    def _values_var(self, varname, ctx):
        # # values[$varname]
        return ast.Subscript(
            value=ast.Name(id='values', ctx=ast.Load()),
            slice=ast.Index(varname),
            ctx=ctx
        )

    def _append_attributes(self):
        # t_attrs = self._post_processing_att(tagName, t_attrs, options)
        # for name, value in t_attrs.items():
        #     if value or isinstance(value, string_types)):
        #         append(u' ')
        #         append(name)
        #         append(u'="')
        #         append(escape(pycompat.to_text((value)))
        #         append(u'"')
        return [
            ast.Assign(
                targets=[ast.Name(id='t_attrs', ctx=ast.Store())],
                value=ast.Call(
                    func=ast.Attribute(
                        value=ast.Name(id='self', ctx=ast.Load()),
                        attr='_post_processing_att',
                        ctx=ast.Load()
                    ),
                    args=[
                        ast.Name(id='tagName', ctx=ast.Load()),
                        ast.Name(id='t_attrs', ctx=ast.Load()),
                        ast.Name(id='options', ctx=ast.Load()),
                    ], keywords=[],
                    starargs=None, kwargs=None
                )
            ),
            ast.For(
                target=ast.Tuple(elts=[ast.Name(id='name', ctx=ast.Store()), ast.Name(id='value', ctx=ast.Store())], ctx=ast.Store()),
                iter=ast.Call(
                    func=ast.Attribute(
                        value=ast.Name(id='t_attrs', ctx=ast.Load()),
                        attr='items',
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
                                    ast.Name(id='str', ctx=ast.Load())
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
                            args=[ast.Call(
                                func=ast.Name(id='to_text', ctx=ast.Load()),
                                args=[ast.Name(id='value', ctx=ast.Load())], keywords=[],
                                starargs=None, kwargs=None
                            )], keywords=[],
                            starargs=None, kwargs=None
                        )),
                        self._append(ast.Str(u'"')),
                    ],
                    orelse=[]
                )],
                orelse=[]
            )
        ]

    # order

    def _directives_eval_order(self):
        """ List all supported directives in the order in which they should be
        evaluated on a given element. For instance, a node bearing both
        ``foreach`` and ``if`` should see ``foreach`` executed before ``if`` aka
        .. code-block:: xml
            <el t-foreach="foo" t-as="bar" t-if="bar">
        should be equivalent to
        .. code-block:: xml
            <t t-foreach="foo" t-as="bar">
                <t t-if="bar">
                    <el>
        then this method should return ``['foreach', 'if']``.
        """
        return [
            'debug',
            'groups', 'foreach', 'if', 'elif', 'else',
            'field', 'esc', 'raw',
            'tag',
            'call',
            'set',
            'content',
        ]

    def _is_static_node(self, el, options):
        """ Test whether the given element is purely static, i.e., does not
        require dynamic rendering for its attributes.
        """
        return not any(att.startswith('t-') for att in el.attrib)

    # compile

    def _compile_start_profiling(self, el, directive, options):
        if 'profile' not in options:
            return []

        ref = options['ref']
        path = options['root'].getpath(el) if el is not None else ''
        loginfo = 'loginfo_%s_%s' % (path, directive)

        return [
            # loginfo = self._hook_before_directive(ref, path, directive, values, options)
            ast.Assign(
                targets=[ast.Name(id=loginfo, ctx=ast.Store())],
                value=ast.Call(
                    func=ast.Attribute(
                        value=ast.Name(id='self', ctx=ast.Load()),
                        attr='_hook_before_directive',
                        ctx=ast.Load()
                    ),
                    args=[
                        ast.Num(ref) if isinstance(ref, int) else ast.Str(ref),
                        ast.Str(s=options.get('document')),
                        ast.Str(path),
                        ast.Str(directive or ''),
                        ast.Name(id='values', ctx=ast.Load()),
                        ast.Name(id='options', ctx=ast.Load()),
                    ],
                    keywords=[], starargs=None, kwargs=None
                )
            ),
        ]

    def _compile_stop_profiling(self, el, directive, options):
        if 'profile' not in options:
            return []

        ref = options['ref']
        path = options['root'].getpath(el) if el is not None else ''
        loginfo = 'loginfo_%s_%s' % (path, directive)

        return [
            # self._hook_after_directive(ref, path, directive, values, options, loginfo)
            ast.Expr(ast.Call(
                func=ast.Attribute(
                    value=ast.Name(id='self', ctx=ast.Load()),
                    attr='_hook_after_directive',
                    ctx=ast.Load()
                ),
                args=[
                    ast.Num(ref) if isinstance(ref, int) else ast.Str(ref),
                    ast.Str(s=options.get('document')),
                    ast.Str(path),
                    ast.Str(directive or ''),
                    ast.Name(id='values', ctx=ast.Load()),
                    ast.Name(id='options', ctx=ast.Load()),
                    ast.Name(id=loginfo, ctx=ast.Load()),
                ],
                keywords=[], starargs=None, kwargs=None
            ))
        ]

    def _compile_static_node(self, el, options):
        """ Compile a purely static element into a list of AST nodes. """
        if not el.nsmap:
            unqualified_el_tag = el_tag = el.tag
            content = self._compile_directive_content(el, options)
            attrib = self._post_processing_att(el.tag, el.attrib, options)
        else:
            # Etree will remove the ns prefixes indirection by inlining the corresponding
            # nsmap definition into the tag attribute. Restore the tag and prefix here.
            unqualified_el_tag = etree.QName(el.tag).localname
            el_tag = unqualified_el_tag
            if el.prefix:
                el_tag = '%s:%s' % (el.prefix, el_tag)

            attrib = {}
            # If `el` introduced new namespaces, write them as attribute by using the
            # `attrib` dict.
            for ns_prefix, ns_definition in set(el.nsmap.items()) - set(options['nsmap'].items()):
                if ns_prefix is None:
                    attrib['xmlns'] = ns_definition
                else:
                    attrib['xmlns:%s' % ns_prefix] = ns_definition

            # Etree will also remove the ns prefixes indirection in the attributes. As we only have
            # the namespace definition, we'll use an nsmap where the keys are the definitions and
            # the values the prefixes in order to get back the right prefix and restore it.
            ns = itertools.chain(options['nsmap'].items(), el.nsmap.items())
            nsprefixmap = {v: k for k, v in ns}
            for key, value in el.attrib.items():
                attrib_qname = etree.QName(key)
                if attrib_qname.namespace:
                    attrib['%s:%s' % (nsprefixmap[attrib_qname.namespace], attrib_qname.localname)] = value
                else:
                    attrib[key] = value

            attrib = self._post_processing_att(el.tag, attrib, options)

            # Update the dict of inherited namespaces before continuing the recursion. Note:
            # since `options['nsmap']` is a dict (and therefore mutable) and we do **not**
            # want changes done in deeper recursion to bevisible in earlier ones, we'll pass
            # a copy before continuing the recursion and restore the original afterwards.
            original_nsmap = dict(options['nsmap'])
            options['nsmap'].update(el.nsmap)
            content = self._compile_directive_content(el, options)
            options['nsmap'] = original_nsmap

        directive = '<%s>' % el_tag
        start = self._compile_start_profiling(el, directive, options)
        end = self._compile_stop_profiling(el, directive, options)

        if unqualified_el_tag == 't':
            return start + end + content
        tag = u'<%s%s' % (el_tag, u''.join([u' %s="%s"' % (name, escape(pycompat.to_text(value))) for name, value in attrib.items()]))
        if unqualified_el_tag in self._void_elements:
            return start + [self._append(ast.Str(tag + '/>'))] + end + content
        else:
            return start + [self._append(ast.Str(tag + '>'))] + end + content + [self._append(ast.Str('</%s>' % el_tag))]

    def _compile_static_attributes(self, el, options):
        """ Compile the static attributes of the given element into a list of
        pairs (name, expression AST). """
        # Etree will also remove the ns prefixes indirection in the attributes. As we only have
        # the namespace definition, we'll use an nsmap where the keys are the definitions and
        # the values the prefixes in order to get back the right prefix and restore it.
        nsprefixmap = {v: k for k, v in itertools.chain(options['nsmap'].items(), el.nsmap.items())}

        nodes = []
        for key, value in el.attrib.items():
            if not key.startswith('t-'):
                attrib_qname = etree.QName(key)
                if attrib_qname.namespace:
                    key = '%s:%s' % (nsprefixmap[attrib_qname.namespace], attrib_qname.localname)
                nodes.append((key, ast.Str(value), None, None))
        return nodes

    def _compile_dynamic_attributes(self, el, options):
        """ Compile the dynamic attributes of the given element into a list of
        pairs (name, expression AST).

        We do not support namespaced dynamic attributes.
        """
        nodes = []
        for name, value in el.attrib.items():
            directive = '%s="%s"' % (name, value)
            start = self._compile_start_profiling(el, directive, options)
            stop = self._compile_stop_profiling(el, directive, options)

            if name.startswith('t-attf-'):
                nodes.append((name[7:], self._compile_format(value), start, stop))
            elif name.startswith('t-att-'):
                nodes.append((name[6:], self._compile_expr(value), start, stop))
            elif name == 't-att':
                # self._get_dynamic_att($tag, $value, options, values)
                fn = ast.Call(
                    func=ast.Attribute(
                        value=ast.Name(id='self', ctx=ast.Load()),
                        attr='_get_dynamic_att',
                        ctx=ast.Load()
                    ),
                    args=[
                        ast.Str(el.tag),
                        self._compile_expr(value),
                        ast.Name(id='options', ctx=ast.Load()),
                        ast.Name(id='values', ctx=ast.Load()),
                    ], keywords=[],
                    starargs=None, kwargs=None
                )
                nodes.append((fn, None, start, stop))
        return nodes

    def _compile_all_attributes(self, el, options, attr_already_created=False):
        """ Compile the attributes of the given elements into a list of AST nodes. """
        body = []
        if any(name.startswith('t-att') or not name.startswith('t-') for name, value in el.attrib.items()):
            if not attr_already_created:
                attr_already_created = True
                body.append(
                    # t_attrs = OrderedDict()
                    ast.Assign(
                        targets=[ast.Name(id='t_attrs', ctx=ast.Store())],
                        value=ast.Call(
                            func=ast.Name(id='OrderedDict', ctx=ast.Load()),
                            args=[],
                            keywords=[], starargs=None, kwargs=None
                        )
                    )
                )

            items = self._compile_static_attributes(el, options) + self._compile_dynamic_attributes(el, options)
            for item in items:
                if item[2]:
                    body.extend(item[2])
                if item[1]:
                    # t_attrs[$name] = $value
                    body.append(ast.Assign(
                        targets=[ast.Subscript(
                            value=ast.Name(id='t_attrs', ctx=ast.Load()),
                            slice=ast.Index(ast.Str(item[0])),
                            ctx=ast.Store()
                        )],
                        value=item[1]
                    ))
                elif item:
                    # t_attrs.update($item)
                    body.append(ast.Expr(ast.Call(
                        func=ast.Attribute(
                            value=ast.Name(id='t_attrs', ctx=ast.Load()),
                            attr='update',
                            ctx=ast.Load()
                        ),
                        args=[item[0]],
                        keywords=[],
                        starargs=None, kwargs=None
                    )))
                if item[3]:
                    body.extend(item[3])

        if attr_already_created:
            # tagName = $el.tag
            body.append(ast.Assign(
                targets=[ast.Name(id='tagName', ctx=ast.Store())],
                value=ast.Str(el.tag))
            )
            body.extend(self._append_attributes())

        return body

    def _compile_tag(self, el, content, options, attr_already_created=False):
        """ Compile the tag of the given element into a list of AST nodes. """
        extra_attrib = {}
        if not el.nsmap:
            unqualified_el_tag = el_tag = el.tag
        else:
            # Etree will remove the ns prefixes indirection by inlining the corresponding
            # nsmap definition into the tag attribute. Restore the tag and prefix here.
            # Note: we do not support namespace dynamic attributes.
            unqualified_el_tag = etree.QName(el.tag).localname
            el_tag = unqualified_el_tag
            if el.prefix:
                el_tag = '%s:%s' % (el.prefix, el_tag)

            # If `el` introduced new namespaces, write them as attribute by using the
            # `extra_attrib` dict.
            for ns_prefix, ns_definition in set(el.nsmap.items()) - set(options['nsmap'].items()):
                if ns_prefix is None:
                    extra_attrib['xmlns'] = ns_definition
                else:
                    extra_attrib['xmlns:%s' % ns_prefix] = ns_definition

        if unqualified_el_tag == 't':
            return content

        directive = '<%s>' % el_tag

        body = self._compile_start_profiling(el, directive, options)
        body.append(self._append(ast.Str(u'<%s%s' % (el_tag, u''.join([u' %s="%s"' % (name, escape(pycompat.to_text(value))) for name, value in extra_attrib.items()])))))
        body.extend(self._compile_stop_profiling(el, directive, options))
        body.extend(self._compile_all_attributes(el, options, attr_already_created))
        if unqualified_el_tag in self._void_elements:
            body.append(self._append(ast.Str(u'/>')))
            body.extend(content)
        else:
            body.append(self._append(ast.Str(u'>')))
            body.extend(content)
            body.append(self._append(ast.Str(u'</%s>' % el_tag)))
        return body

    # compile directives

    def _compile_directive_debug(self, el, options):
        debugger = el.attrib.pop('t-debug')
        body = self._compile_directives(el, options)
        if options['dev_mode']:
            body = ast.parse("__import__('%s').set_trace()" % re.sub(r'[^a-zA-Z]', '', debugger)).body + body  # pdb, ipdb, pudb, ...
        else:
            _logger.warning("@t-debug in template is only available in dev mode options")
        return body

    def _compile_directive_tag(self, el, options):
        el.attrib.pop('t-tag', None)

        # Update the dict of inherited namespaces before continuing the recursion. Note:
        # since `options['nsmap']` is a dict (and therefore mutable) and we do **not**
        # want changes done in deeper recursion to bevisible in earlier ones, we'll pass
        # a copy before continuing the recursion and restore the original afterwards.
        original_nsmap = dict(options['nsmap'])
        if el.nsmap:
            options['nsmap'].update(el.nsmap)
        content = self._compile_directives(el, options)
        if el.nsmap:
            options['nsmap'] = original_nsmap
        return self._compile_tag(el, content, options, False)

    def _compile_directive_set(self, el, options):
        varname = el.attrib.pop('t-set')
        directive = 't-set="%s"' % varname

        if 't-value' in el.attrib:
            expr = el.attrib.pop('t-value')
            directive = '%s t-value="%s"' % (directive, expr)
            value = self._compile_expr(expr or 'None')
        elif 't-valuef' in el.attrib:
            expr = el.attrib.pop('t-valuef')
            directive = '%s t-valuef="%s"' % (directive, expr)
            value = self._compile_format(expr)
        else:
            # set the content as value
            body = self._compile_directive_content(el, options)
            if body:
                def_name = self._create_def(options, body, prefix='set', lineno=el.sourceline)
                return self._compile_start_profiling(el, directive, options) + [
                    # content = []
                    ast.Assign(
                        targets=[ast.Name(id='content', ctx=ast.Store())],
                        value=ast.List(elts=[], ctx=ast.Load())
                    ),
                    # set(self, $varset.append)
                    ast.Expr(self._call_def(
                        def_name,
                        append=ast.Attribute(
                            value=ast.Name(id='content', ctx=ast.Load()),
                            attr='append',
                            ctx=ast.Load()
                        )
                    )),
                    # $varset = u''.join($varset)
                    ast.Assign(
                        targets=[self._values_var(ast.Str(varname), ctx=ast.Store())],
                        value=ast.Call(
                            func=ast.Attribute(value=ast.Str(u''), attr='join', ctx=ast.Load()),
                            args=[ast.Name(id='content', ctx=ast.Load())], keywords=[],
                            starargs=None, kwargs=None
                        )
                    )
                ] + self._compile_stop_profiling(el, directive, options)
            else:
                value = ast.Str(u'')

        body = self._compile_start_profiling(el, directive, options)
        # $varset = $value
        body.append(ast.Assign(
            targets=[self._values_var(ast.Str(varname), ctx=ast.Store())],
            value=value
        ))
        body.extend(self._compile_stop_profiling(el, directive, options))
        return body

    def _compile_directive_content(self, el, options):
        body = []
        if el.text is not None:
            body.append(self._append(ast.Str(pycompat.to_text(el.text))))
        if el.getchildren():
            for item in el:
                # ignore comments & processing instructions
                if isinstance(item, etree._Comment):
                    continue
                body.extend(self._compile_node(item, options))
                body.extend(self._compile_tail(item))
        return body

    def _compile_directive_else(self, el, options):
        if el.attrib.pop('t-else') == '_t_skip_else_':
            return []
        if not options.pop('t_if', None):
            raise ValueError("t-else directive must be preceded by t-if directive")
        compiled = self._compile_directives(el, options)
        el.attrib['t-else'] = '_t_skip_else_'
        return compiled

    def _compile_directive_elif(self, el, options):
        _elif = el.attrib.pop('t-elif')
        if _elif == '_t_skip_else_':
            return []
        if not options.pop('t_if', None):
            raise ValueError("t-elif directive must be preceded by t-if directive")
        el.attrib['t-temp-elif'] = _elif
        compiled = self._compile_directive_if(el, options)
        el.attrib['t-elif'] = '_t_skip_else_'
        return compiled

    def _compile_directive_if(self, el, options):
        orelse = []
        next_el = el.getnext()
        comments_to_remove = []
        while isinstance(next_el, etree._Comment):
            comments_to_remove.append(next_el)
            next_el = next_el.getnext()

        if next_el is not None and {'t-else', 't-elif'} & set(next_el.attrib):
            parent = el.getparent()
            for comment in comments_to_remove:
                parent.remove(comment)
            if el.tail and not el.tail.isspace():
                raise ValueError("Unexpected non-whitespace characters between t-if and t-else directives")
            el.tail = None
            orelse = self._compile_node(next_el, dict(options, t_if=True))

        directive = 't-elif="%s"' if 't-temp-elif' in el.attrib else 't-if="%s"'
        expr = el.attrib.pop('t-temp-elif', el.attrib.pop('t-if', None))
        directive = directive % expr
        return self._compile_start_profiling(el, directive, options) + [
            # if $t-if:
            #    next tag directive
            # else:
            #    $t-else
            ast.If(
                test=self._compile_expr(expr),
                body=(self._compile_stop_profiling(el, directive, options) + self._compile_directives(el, options)) or [ast.Pass()],
                orelse=self._compile_stop_profiling(el, directive, options) + orelse
            )
        ]

    def _compile_directive_groups(self, el, options):
        groups = el.attrib.pop('t-groups')
        expr = 'groups="%s"' % groups
        return self._compile_start_profiling(el, expr, options) + [
            # if self.user_has_groups($groups):
            #    next tag directive
            ast.If(
                test=ast.Call(
                    func=ast.Attribute(
                        value=ast.Name(id='self', ctx=ast.Load()),
                        attr='user_has_groups',
                        ctx=ast.Load()
                    ),
                    args=[ast.Str(groups)], keywords=[],
                    starargs=None, kwargs=None
                ),
                body=(self._compile_stop_profiling(el, expr, options) + self._compile_directives(el, options)) or [ast.Pass()],
                orelse=self._compile_stop_profiling(el, expr, options)
            )
        ]

    def _compile_directive_foreach(self, el, options):
        expr_foreach = el.attrib.pop('t-foreach')
        expr_as = el.attrib.pop('t-as')
        expr = self._compile_expr(expr_foreach)
        varname = expr_as.replace('.', '_')
        values = self._make_name('values')
        directive = 't-foreach="%s" t-as="%s"' % (expr_foreach, expr_as)

        # create function $foreach
        def_name = self._create_def(options, self._compile_directives(el, options), prefix='foreach', lineno=el.sourceline)

        body = [ast.Expr(self._call_def(def_name, values=values))]
        if 'profile' in options:
            # if values[$varname_first]:
            #    self._hook_after_directive(template, path, directive, options, loginfo)
            # body
            # if values[$varname_last]:
            #    break # add this line to not use orelse
            body = [ast.If(
                    test=ast.Subscript(
                        value=ast.Name(id=values, ctx=ast.Load()),
                        slice=ast.Index(ast.Str('%s_first' % varname)),
                        ctx=ast.Load(),
                    ),
                    body=self._compile_stop_profiling(el, directive, options),
                    orelse=[],
                )
                ] + body + [
                    ast.If(
                    test=ast.Subscript(
                        value=ast.Name(id=values, ctx=ast.Load()),
                        slice=ast.Index(ast.Str('%s_last' % varname)),
                        ctx=ast.Load(),
                    ),
                    body=[ast.Break()],
                    orelse=[],
                )]

        # for $values in foreach_iterator(values, $expr, $varname):
        #     $foreach(self, append, $values, options)
        return self._compile_start_profiling(el, directive, options) + [ast.For(
            target=ast.Name(id=values, ctx=ast.Store()),
            iter=ast.Call(
                func=ast.Name(id='foreach_iterator', ctx=ast.Load()),
                args=[ast.Name(id='values', ctx=ast.Load()), expr, ast.Str(varname)],
                keywords=[], starargs=None, kwargs=None
            ),
            body=body,
            orelse=self._compile_stop_profiling(el, directive, options)
        )]

    def _compile_tail(self, el):
        return el.tail is not None and [self._append(ast.Str(pycompat.to_text(el.tail)))] or []

    def _compile_directive_esc(self, el, options):
        field_options = self._compile_widget_options(el)
        expr = el.attrib.pop('t-esc')
        directive = 't-esc="%s"' % expr
        content = self._compile_widget(el, expr, field_options)
        if not field_options:
            # if content is not False and if content is not None:
            #     content = escape(pycompat.to_text(content))
            content.append(self._if_content_is_not_Falsy([
                ast.Assign(
                    targets=[ast.Name(id='content', ctx=ast.Store())],
                    value=ast.Call(
                        func=ast.Name(id='escape', ctx=ast.Load()),
                        args=[ast.Call(
                            func=ast.Name(id='to_text', ctx=ast.Load()),
                            args=[ast.Name(id='content', ctx=ast.Load())], keywords=[],
                            starargs=None, kwargs=None
                        )],
                        keywords=[],
                        starargs=None, kwargs=None
                    )
                )],
                []
            ))
        return self._compile_start_profiling(el, directive, options) + content + self._compile_widget_value(el, options) + self._compile_stop_profiling(el, directive, options)

    def _compile_directive_raw(self, el, options):
        field_options = self._compile_widget_options(el)
        expr = el.attrib.pop('t-raw')
        directive = 't-raw="%s"' % expr
        content = self._compile_widget(el, expr, field_options)
        return self._compile_start_profiling(el, directive, options) + content + self._compile_widget_value(el, options) + self._compile_stop_profiling(el, directive, options)

    def _compile_widget(self, el, expression, field_options):
        if field_options:
            return [
                # content = t-(esc|raw)
                ast.Assign(
                    targets=[ast.Name(id='content', ctx=ast.Store())],
                    value=self._compile_expr0(expression)
                ),
                # t_attrs, content, force_display = self._get_widget(value, expression, tagName, field options, template options, values)
                ast.Assign(
                    targets=[ast.Tuple(elts=[
                        ast.Name(id='t_attrs', ctx=ast.Store()),
                        ast.Name(id='content', ctx=ast.Store()),
                        ast.Name(id='force_display', ctx=ast.Store())
                    ], ctx=ast.Store())],
                    value=ast.Call(
                        func=ast.Attribute(
                            value=ast.Name(id='self', ctx=ast.Load()),
                            attr='_get_widget',
                            ctx=ast.Load()
                        ),
                        args=[
                            ast.Name(id='content', ctx=ast.Load()),
                            ast.Str(expression),
                            ast.Str(el.tag),
                            field_options,
                            ast.Name(id='options', ctx=ast.Load()),
                            ast.Name(id='values', ctx=ast.Load()),
                        ],
                        keywords=[], starargs=None, kwargs=None
                    )
                )
            ]

        return [
            # t_attrs, content, force_display = OrderedDict(), t-(esc|raw), None
            ast.Assign(
                targets=[ast.Tuple(elts=[
                    ast.Name(id='t_attrs', ctx=ast.Store()),
                    ast.Name(id='content', ctx=ast.Store()),
                    ast.Name(id='force_display', ctx=ast.Store()),
                ], ctx=ast.Store())],
                value=ast.Tuple(elts=[
                    ast.Call(
                        func=ast.Name(id='OrderedDict', ctx=ast.Load()),
                        args=[],
                        keywords=[], starargs=None, kwargs=None
                    ),
                    self._compile_expr0(expression),
                    ast.Constant(None),
                ], ctx=ast.Load())
            )
        ]

    def _compile_widget_options(self, el):
        """
        compile t-options and add to the dict the t-options-xxx values
        """
        options = el.attrib.pop('t-options', None)
        # the options can be None, a dict {}, or the method dict()
        ast_options = options and self._compile_expr(options) or ast.Dict(keys=[], values=[])

        # convert ast.Call from dict() into ast.Dict
        if isinstance(ast_options, ast.Call):
            ast_options = ast.Dict(
                keys=[ast.Str(k.arg) for k in ast_options.keywords],
                values=[k.value for k in ast_options.keywords]
            )

        for complete_key in OrderedDict(el.attrib):
            if complete_key.startswith('t-options-'):
                key = complete_key[10:]
                value = self._compile_expr(el.attrib.pop(complete_key))

                replacement = False
                for astStr in ast_options.keys:
                    if astStr.s == key:
                        ast_options.values[ast_options.keys.index(astStr)] = value
                        replacement = True
                        break

                if not replacement:
                    ast_options.keys.append(ast.Str(key))
                    ast_options.values.append(value)

        return ast_options if ast_options and ast_options.keys else None

    def _compile_directive_field(self, el, options):
        """ Compile something like ``<span t-field="record.phone">+1 555 555 8069</span>`` """
        node_name = el.tag
        assert node_name not in ("table", "tbody", "thead", "tfoot", "tr", "td",
                                 "li", "ul", "ol", "dl", "dt", "dd"),\
            "RTE widgets do not work correctly on %r elements" % node_name
        assert node_name != 't',\
            "t-field can not be used on a t element, provide an actual HTML node"
        assert "." in el.get('t-field'),\
            "t-field must have at least a dot like 'record.field_name'"

        expression = el.attrib.pop('t-field')
        directive = 't-field="%s"' % expression
        field_options = self._compile_widget_options(el) or ast.Dict(keys=[], values=[])
        record, field_name = expression.rsplit('.', 1)

        body = self._compile_start_profiling(el, directive, options)
        body.append(
            # t_attrs, content, force_display = self._get_field(record, field_name, expression, tagName, field options, template options, values)
            ast.Assign(
                targets=[ast.Tuple(elts=[
                    ast.Name(id='t_attrs', ctx=ast.Store()),
                    ast.Name(id='content', ctx=ast.Store()),
                    ast.Name(id='force_display', ctx=ast.Store())
                ], ctx=ast.Store())],
                value=ast.Call(
                    func=ast.Attribute(
                        value=ast.Name(id='self', ctx=ast.Load()),
                        attr='_get_field',
                        ctx=ast.Load()
                    ),
                    args=[
                        self._compile_expr(record),
                        ast.Str(field_name),
                        ast.Str(expression),
                        ast.Str(node_name),
                        field_options,
                        ast.Name(id='options', ctx=ast.Load()),
                        ast.Name(id='values', ctx=ast.Load()),
                    ],
                    keywords=[], starargs=None, kwargs=None
                )
            )
        )
        body.extend(self._compile_widget_value(el, options))
        body.extend(self._compile_stop_profiling(el, directive, options))
        return body

    def _compile_widget_value(self, el, options):
        el.attrib.pop('t-tag', None)

        # if force_display:
        #    display the tag without content
        orelse = [ast.If(
            test=ast.Name(id='force_display', ctx=ast.Load()),
            body=self._compile_tag(el, [], options, True) or [ast.Pass()],
            orelse=[],
        )]

        # default content
        default_content = self._make_name('default_content')
        body = self._compile_directive_content(el, options)
        if body:
            orelse = [
                # default_content = []
                ast.Assign(
                    targets=[ast.Name(id=default_content, ctx=ast.Store())],
                    value=ast.List(elts=[], ctx=ast.Load())
                ),
                # body_call_content(self, default_content.append, values, options)
                ast.Expr(self._call_def(
                    self._create_def(options, body, prefix='body_call_content', lineno=el.sourceline),
                    append=ast.Attribute(
                        value=ast.Name(id=default_content, ctx=ast.Load()),
                        attr='append',
                        ctx=ast.Load()
                    )
                )),
                # default_content = u''.join(default_content)
                ast.Assign(
                    targets=[ast.Name(id=default_content, ctx=ast.Store())],
                    value=ast.Call(
                        func=ast.Attribute(
                            value=ast.Str(u''),
                            attr='join',
                            ctx=ast.Load()
                        ),
                        args=[
                            ast.Name(id=default_content, ctx=ast.Load())
                        ],
                        keywords=[], starargs=None, kwargs=None
                    )
                ),
                # if default_content:
                #    display the tag with default content
                # elif force_display:
                #    display the tag without content
                ast.If(
                    test=ast.Name(id=default_content, ctx=ast.Load()),
                    body=self._compile_tag(el, [self._append(ast.Name(id=default_content, ctx=ast.Load()))], options, True) or [ast.Pass()],
                    orelse=orelse,
                )
            ]

        # if content is not None:
        #    display the tag (to_text(content))
        # else
        #    if default_content:
        #       display the tag with default content
        #    elif force_display:
        #       display the tag without content
        return [self._if_content_is_not_Falsy(
            body=self._compile_tag(el, [self._append(
                ast.Call(
                    func=ast.Name(id='to_text', ctx=ast.Load()),
                    args=[ast.Name(id='content', ctx=ast.Load())], keywords=[],
                    starargs=None, kwargs=None
                )
            )], options, True),
            orelse=orelse,
        )]

    def _compile_directive_call(self, el, options):
        tmpl = el.attrib.pop('t-call')
        directive = 't-call="%s"' % tmpl
        _values = self._make_name('values_copy')
        call_options = el.attrib.pop('t-call-options', None)
        nsmap = options.get('nsmap')

        _values = self._make_name('values_copy')

        content = [
            # values_copy = values.copy()
            ast.Assign(
                targets=[ast.Name(id=_values, ctx=ast.Store())],
                value=ast.Call(
                    func=ast.Attribute(
                        value=ast.Name(id='values', ctx=ast.Load()),
                        attr='copy',
                        ctx=ast.Load()
                    ),
                    args=[], keywords=[],
                    starargs=None, kwargs=None
                )
            )
        ]

        body = self._compile_directive_content(el, options)
        if body:
            def_name = self._create_def(options, body, prefix='body_call_content', lineno=el.sourceline)

            # call_content = []
            content.append(
                ast.Assign(
                    targets=[ast.Name(id='call_content', ctx=ast.Store())],
                    value=ast.List(elts=[], ctx=ast.Load())
                )
            )
            # body_call_content(self, call_content.append, values, options)
            content.append(
                ast.Expr(self._call_def(
                    def_name,
                    append=ast.Attribute(
                        value=ast.Name(id='call_content', ctx=ast.Load()),
                        attr='append',
                        ctx=ast.Load()
                    ),
                    values=_values
                ))
            )
            # values_copy[0] = call_content
            content.append(
                ast.Assign(
                    targets=[ast.Subscript(
                        value=ast.Name(id=_values, ctx=ast.Load()),
                        slice=ast.Index(ast.Num(0)),
                        ctx=ast.Store()
                    )],
                    value=ast.Name(id='call_content', ctx=ast.Load())
                )
            )
        else:
            # values_copy[0] = []
            content.append(
                ast.Assign(
                    targets=[ast.Subscript(
                        value=ast.Name(id=_values, ctx=ast.Load()),
                        slice=ast.Index(ast.Num(0)),
                        ctx=ast.Store()
                    )],
                    value=ast.List(elts=[], ctx=ast.Load())
                )
            )

        name_options = self._make_name('options')
        # copy the original dict of options to pass to the callee
        content.append(
            # options_ = options.copy()
            ast.Assign(
                targets=[ast.Name(id=name_options, ctx=ast.Store())],
                value=ast.Call(
                    func=ast.Attribute(
                        value=ast.Name(id='options', ctx=ast.Load()),
                        attr='copy',
                        ctx=ast.Load()
                    ),
                    args=[], keywords=[], starargs=None, kwargs=None
                )
            )
        )
        if nsmap or call_options:

            if call_options:
                # update this dict with the content of `t-call-options`
                content.extend([
                    # options_.update(template options)
                    ast.Expr(ast.Call(
                        func=ast.Attribute(
                            value=ast.Name(id=name_options, ctx=ast.Load()),
                            attr='update',
                            ctx=ast.Load()
                        ),
                        args=[self._compile_expr(call_options)],
                        keywords=[], starargs=None, kwargs=None
                    )),

                    # if options.get('lang') != options_.get('lang'):
                    #   self = self.with_context(lang=options.get('lang'))
                    ast.If(
                        test=ast.Compare(
                            left=ast.Call(
                                func=ast.Attribute(
                                    value=ast.Name(id='options', ctx=ast.Load()),
                                    attr='get',
                                    ctx=ast.Load()
                                ),
                                args=[ast.Str("lang")], keywords=[],
                                starargs=None, kwargs=None
                            ),
                            ops=[ast.NotEq()],
                            comparators=[ast.Call(
                                func=ast.Attribute(
                                    value=ast.Name(id=name_options, ctx=ast.Load()),
                                    attr='get',
                                    ctx=ast.Load()
                                ),
                                args=[ast.Str("lang")], keywords=[],
                                starargs=None, kwargs=None
                            )]
                        ),
                        body=[
                            ast.Assign(
                                targets=[ast.Name(id='self', ctx=ast.Store())],
                                value=ast.Call(
                                    func=ast.Attribute(
                                        value=ast.Name(id='self', ctx=ast.Load()),
                                        attr='with_context',
                                        ctx=ast.Load()
                                    ),
                                    args=[],
                                    keywords=[ast.keyword('lang', ast.Call(
                                        func=ast.Attribute(
                                            value=ast.Name(id=name_options, ctx=ast.Load()),
                                            attr='get',
                                            ctx=ast.Load()
                                        ),
                                        args=[ast.Str("lang")], keywords=[],
                                        starargs=None, kwargs=None
                                    ))],
                                    starargs=None, kwargs=None
                                )
                            )],
                        orelse=[],
                    )
                ])

            if nsmap:
                # update this dict with the current nsmap so that the callee know
                # if he outputting the xmlns attributes is relevenat or not

                # make the nsmap an ast dict
                keys = []
                values = []
                for key, value in options['nsmap'].items():
                    if isinstance(key, str):
                        keys.append(ast.Str(s=key))
                    elif key is None:
                        keys.append(ast.Constant(None))
                    values.append(ast.Str(s=value))

                # {'nsmap': {None: 'xmlns def'}}
                nsmap_ast_dict = ast.Dict(
                    keys=[ast.Str(s='nsmap')],
                    values=[ast.Dict(keys=keys, values=values)]
                )

                # options_.update(nsmap_ast_dict)
                content.append(
                    ast.Expr(ast.Call(
                        func=ast.Attribute(
                            value=ast.Name(id=name_options, ctx=ast.Load()),
                            attr='update',
                            ctx=ast.Load()
                        ),
                        args=[nsmap_ast_dict],
                        keywords=[], starargs=None, kwargs=None
                    ))
                )

        # options_.update({
        #     'caller_template': str(options.get('template')),
        #     'last_path_node': str(options['root'].getpath(el)),
        # })
        content.append(
            ast.Expr(ast.Call(
                func=ast.Attribute(
                    value=ast.Name(id=name_options, ctx=ast.Load()),
                    attr='update',
                    ctx=ast.Load()
                ),
                args=[
                    ast.Dict(
                        keys=[ast.Str(s='caller_template'), ast.Str(s='last_path_node')],
                        values=[
                            ast.Str(s=str(options.get('template'))),
                            ast.Str(s=str(options['root'].getpath(el))),
                        ]
                    )
                ],
                keywords=[], starargs=None, kwargs=None
            ))
        )

        # self.compile($tmpl, options)(self, append, values_copy)
        content.append(
            ast.Expr(ast.Call(
                func=ast.Call(
                    func=ast.Attribute(
                        value=ast.Name(id='self', ctx=ast.Load()),
                        attr='compile',
                        ctx=ast.Load()
                    ),
                    args=[
                        self._compile_format(str(tmpl)),
                        ast.Name(id=name_options, ctx=ast.Load()),
                    ],
                    keywords=[], starargs=None, kwargs=None
                ),
                args=[
                    ast.Name(id='self', ctx=ast.Load()),
                    ast.Name(id='append', ctx=ast.Load()),
                    ast.Name(id=_values, ctx=ast.Load())
                ],
                keywords=[], starargs=None, kwargs=None
            ))
        )

        return self._compile_start_profiling(el, directive, options) + content + self._compile_stop_profiling(el, directive, options)

    # method called by computing code

    def _get_dynamic_att(self, tagName, atts, options, values):
        if isinstance(atts, OrderedDict):
            return atts
        if isinstance(atts, (list, tuple)) and not isinstance(atts[0], (list, tuple)):
            atts = [atts]
        if isinstance(atts, (list, tuple)):
            atts = OrderedDict(atts)
        return atts

    def _post_processing_att(self, tagName, atts, options):
        """ Method called by the compiled code. This method may be overwrited
            to filter or modify the attributes after they are compiled.

            @returns OrderedDict
        """
        return atts

    def _get_field(self, record, field_name, expression, tagName, field_options, options, values):
        """
        :returns: tuple:
            * OrderedDict: attributes
            * string or None: content
            * boolean: force_display display the tag if the content and default_content are None
        """
        return self._get_widget(getattr(record, field_name, None), expression, tagName, field_options, options, values)

    def _get_widget(self, value, expression, tagName, field_options, options, values):
        """
        :returns: tuple:
            * OrderedDict: attributes
            * string or None: content
            * boolean: force_display display the tag if the content and default_content are None
        """
        return (OrderedDict(), value, False)

    def _hook_before_directive(self, ref, arch, xpath, directive, values, options):
        return time()

    def _hook_after_directive(self, ref, arch, xpath, directive, values, options, loginfo):
        dt = (time() - loginfo) * 1000
        _logger.debug({
            'ref': ref,
            'xpath': xpath,
            'directive': directive,
            'time': loginfo,
            'delay': dt,
        })

    # compile expression

    def _compile_strexpr(self, expr):
        # ensure result is unicode
        return ast.Call(
            func=ast.Name(id='to_text', ctx=ast.Load()),
            args=[self._compile_expr(expr)], keywords=[],
            starargs=None, kwargs=None
        )

    def _compile_expr0(self, expr):
        if expr == "0":
            # u''.join(values.get(0, []))
            return ast.Call(
                func=ast.Attribute(
                    value=ast.Str(u''),
                    attr='join',
                    ctx=ast.Load()
                ),
                args=[
                    ast.Call(
                        func=ast.Attribute(
                            value=ast.Name(id='values', ctx=ast.Load()),
                            attr='get',
                            ctx=ast.Load()
                        ),
                        args=[ast.Num(0), ast.List(elts=[], ctx=ast.Load())], keywords=[],
                        starargs=None, kwargs=None
                    )
                ],
                keywords=[], starargs=None, kwargs=None
            )
        return self._compile_expr(expr)

    def _compile_format(self, f):
        """ Parses the provided format string and compiles it to a single
        expression ast, uses string concatenation via "+".
        """
        elts = []
        base_idx = 0
        for m in _FORMAT_REGEX.finditer(f):
            literal = f[base_idx:m.start()]
            if literal:
                elts.append(ast.Str(literal if isinstance(literal, str) else literal.decode('utf-8')))

            expr = m.group(1) or m.group(2)
            elts.append(self._compile_strexpr(expr))
            base_idx = m.end()
        # string past last regex match
        literal = f[base_idx:]
        if literal:
            elts.append(ast.Str(literal if isinstance(literal, str) else literal.decode('utf-8')))

        return reduce(lambda acc, it: ast.BinOp(
            left=acc,
            op=ast.Add(),
            right=it
        ), elts)

    def _compile_expr(self, expr):
        """ Compiles a purported Python expression to ast, and alter its
        variable references to access values data instead exept for
        python buildins.
        This compile method is unsafe!
        Can be overridden to use a safe eval method.
        """
        # string must be stripped otherwise whitespace before the start for
        # formatting purpose are going to break parse/compile
        st = ast.parse(expr.strip(), mode='eval')
        # ast.Expression().body -> expr
        return Contextifier(builtin_defaults).visit(st).body
