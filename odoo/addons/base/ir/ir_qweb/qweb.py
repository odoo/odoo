# -*- coding: utf-8 -*-
import ast
import logging
import os.path
import re
import traceback

from collections import OrderedDict, Sized, Mapping
from functools import reduce
from itertools import tee, count
from textwrap import dedent

import itertools
from lxml import etree, html
from psycopg2.extensions import TransactionRollbackError
import werkzeug
from werkzeug.utils import escape as _escape

from odoo.tools import pycompat, freehash

try:
    import builtins
    builtin_defaults = {name: getattr(builtins, name) for name in dir(builtins)}
except ImportError:
    # pylint: disable=bad-python3-import
    import __builtin__
    builtin_defaults = {name: getattr(__builtin__, name) for name in dir(__builtin__)}

try:
    import astor
except ImportError:
    astor = None

unsafe_eval = eval

_logger = logging.getLogger(__name__)

# in Python 2, arguments (within the ast.arguments structure) are expressions
# (since they can be tuples), generally
# ast.Name(id: identifyer, ctx=ast.Param()), whereas in Python 3 they are
# ast.arg(arg: identifier, annotation: expr?) provide a toplevel arg()
# function which matches ast.arg producing the relevant ast.Name in Python 2.
arg = getattr(ast, 'arg', lambda arg, annotation: ast.Name(id=arg, ctx=ast.Param()))
# also Python 3's arguments has grown *2* new mandatory arguments, kwonlyargs
# and kw_defaults for keyword-only arguments and their default values (if any)
# so add a shim for *that* based on the signature of Python 3 I guess?
arguments = ast.arguments
if pycompat.PY2:
    arguments = lambda args, vararg, kwonlyargs, kw_defaults, kwarg, defaults: ast.arguments(args=args, vararg=vararg, kwarg=kwarg, defaults=defaults)
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
        if pycompat.PY2:
            names = [arg.id for arg in args.args]
        else:
            names = [arg.arg for arg in args.args]
        if args.vararg: names.append(args.vararg)
        if args.kwarg: names.append(args.kwarg)
        # remap defaults in case there's any
        return ast.copy_location(ast.Lambda(
            args=arguments(
                args=args.args,
                defaults=[self.visit(default) for default in args.defaults],
                vararg=args.vararg,
                kwarg=args.kwarg,
                # assume we don't have any, not sure it's even possible to
                # handle that cross-version
                kwonlyargs=[],
                kw_defaults=[],
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
escape = (lambda text: _escape(text, quote=True)) if getattr(werkzeug, '__version__', '0.0') < '0.9.0' else _escape

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
        enum = pycompat.izip(*tee(enum))
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

    _void_elements = frozenset([
        'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'keygen',
        'link', 'menuitem', 'meta', 'param', 'source', 'track', 'wbr'])
    _name_gen = count()

    def render(self, template, values=None, **options):
        """ render(template, values, **options)

        Render the template specified by the given name.

        :param template: template identifier
        :param dict values: template values to be used for rendering
        :param options: used to compile the template (the dict available for the rendering is frozen)
            * ``load`` (function) overrides the load method
            * ``profile`` (float) profile the rendering (use astor lib) (filter
              profile line with time ms >= profile)
        """
        body = []
        self.compile(template, options)(self, body.append, values or {})
        return u''.join(body).encode('utf8')

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

        element, document = self.get_template(template, options)
        name = element.get('t-name', 'unknown')

        _options['template'] = template
        _options['ast_calls'] = []
        _options['root'] = element.getroottree()
        _options['last_path_node'] = None
        if not options.get('nsmap'):
            _options['nsmap'] = {}

        # generate ast

        astmod = self._base_module()
        try:
            body = self._compile_node(element, _options)
            ast_calls = _options['ast_calls']
            _options['ast_calls'] = []
            def_name = self._create_def(_options, body, prefix='template_%s' % name.replace('.', '_'))
            _options['ast_calls'] += ast_calls
        except QWebException as e:
            raise e
        except Exception as e:
            path = _options['last_path_node']
            element, document = self.get_template(template, options)
            node = element.getroottree().xpath(path) if ':' not in path else None
            raise QWebException("Error when compiling AST", e, path, node and etree.tostring(node[0], encoding='unicode'), name)
        astmod.body.extend(_options['ast_calls'])

        if 'profile' in options:
            self._profiling(astmod, _options)

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
            node = element.getroottree().xpath(path)
            raise QWebException("Error when compiling AST", e, path, node and etree.tostring(node[0], encoding='unicode'), name)

        # return the wrapped function

        def _compiled_fn(self, append, values):
            log = {'last_path_node': None}
            new = self.default_values()
            new.update(values)
            try:
                return compiled(self, append, new, options, log)
            except (QWebException, TransactionRollbackError) as e:
                raise e
            except Exception as e:
                path = log['last_path_node']
                element, document = self.get_template(template, options)
                node = element.getroottree().xpath(path) if ':' not in path else None
                raise QWebException("Error to render compiling AST", e, path, node and etree.tostring(node[0], encoding='unicode'), name)

        return _compiled_fn

    def default_values(self):
        """ Return attributes added to the values for each computed template. """
        return {'format': self.format}

    def get_template(self, template, options):
        """ Retrieve the given template, and return it as a pair ``(element,
        document)``, where ``element`` is an etree, and ``document`` is the
        string document that contains ``element``.
        """
        if isinstance(template, etree._Element):
            document = template
            template = etree.tostring(template)
            return (document, template)
        else:
            try:
                document = options.get('load', self.load)(template, options)
            except QWebException as e:
                raise e
            except Exception as e:
                raise QWebException("load could not load template", name=template)

        if document is not None:
            if isinstance(document, etree._Element):
                element = document
                document = etree.tostring(document)
            elif os.path.exists(document):
                element = etree.parse(document).getroot()
            else:
                element = etree.fromstring(document)

            for node in element:
                if node.get('t-name') == str(template):
                    return (node, document)

        raise QWebException("Template not found", name=template)

    def load(self, template, options):
        """ Load a given template. """
        return template

    # public method for template dynamic values

    def format(self, value, formating, *args, **kwargs):
        format = getattr(self, '_format_func_%s' % formating, None)
        if not format:
            raise ValueError("Unknown format '%s'" % (formating,))
        return format(value, *args, **kwargs)

    # compute helpers

    def _profiling(self, astmod, options):
        """ Add profiling code into the givne module AST. """
        if not astor:
            _logger.warning("Please install astor to display the code profiling")
            return
        code_line = astor.to_source(astmod)

        # code = $code_lines.split(u"\n")
        astmod.body.insert(0, ast.Assign(
            targets=[ast.Name(id='code', ctx=ast.Store())],
            value=ast.Call(
                func=ast.Attribute(
                    value=ast.Str(code_line),
                    attr='split',
                    ctx=ast.Load()
                ),
                args=[ast.Str("\n")], keywords=[],
                starargs=None, kwargs=None
            )
        ))
        code_line = [[l, False] for l in code_line.split('\n')]

        # profiling = {}
        astmod.body.insert(0, ast.Assign(
            targets=[ast.Name(id='profiling', ctx=ast.Store())],
            value=ast.Dict(keys=[], values=[])
        ))
        astmod.body.insert(0, ast.parse("from time import time").body[0])

        line_id = [0]
        def prof(code, time):
            line_id[0] += 1

            # profiling.setdefault($line_id, time() - $time)
            return ast.Expr(ast.Call(
                func=ast.Attribute(
                    value=ast.Name(id='profiling', ctx=ast.Load()),
                    attr='setdefault',
                    ctx=ast.Load()
                ),
                args=[
                    ast.Num(line_id[0]),
                    ast.BinOp(
                        left=ast.Call(
                            func=ast.Name(id='time', ctx=ast.Load()),
                            args=[],
                            keywords=[], starargs=None, kwargs=None
                        ),
                        op=ast.Sub(),
                        right=ast.Name(id=time, ctx=ast.Load())
                    )
                ],
                keywords=[], starargs=None, kwargs=None
            ))

        def profile(body):
            profile_body = []
            for code in body:
                time = self._make_name('time')

                # $time = time()
                profile_body.append(
                    ast.Assign(
                        targets=[ast.Name(id=time, ctx=ast.Store())],
                        value=ast.Call(
                            func=ast.Name(id='time', ctx=ast.Load()),
                            args=[],
                            keywords=[], starargs=None, kwargs=None
                        )
                    )
                )
                profile_body.append(code)
                profline = prof(code, time)
                # log body of if, else and loop
                if hasattr(code, 'body'):
                    code.body = [profline] + profile(code.body)
                    if hasattr(code, 'orelse'):
                        code.orelse = [profline] + profile(code.orelse)
                profile_body.append(profline)

            return profile_body

        for call in options['ast_calls']:
            call.body = profile(call.body)

        options['ast_calls'][0].body = ast.parse(dedent("""
            global profiling
            profiling = {}
            """)).body + options['ast_calls'][0].body

        p = float(options.get('profile'))
        options['ast_calls'][0].body.extend(ast.parse(dedent("""
            total = 0
            prof_total = 0
            code_profile = []
            line_id = 0
            for line in code:
                if not line:
                    if %s <= 0: print ""
                    continue
                if line.startswith('def ') or line.startswith('from ') or line.startswith('import '):
                    if %s <= 0: print "      \t", line
                    continue
                line_id += 1
                total += profiling.get(line_id, 0)
                dt = round(profiling.get(line_id, -1)*1000000)/1000
                if %s <= dt:
                    prof_total += profiling.get(line_id, 0)
                    display = "%%.2f\t" %% dt
                    print (" " * (7 - len(display))) + display, line
                elif dt < 0 and %s <= 0:
                    print "     ?\t", line
            print "'%s' Total: %%d/%%d" %% (round(prof_total*1000), round(total*1000))
            """ % (p, p, p, p, str(options['template']).replace('"', ' ')))).body)

    def _base_module(self):
        """ Base module supporting qweb template functions (provides basic
        imports and utilities), returned as a Python AST.
        Currently provides:
        * collections
        * itertools
        Define:
        * escape
        * to_text (empty string for a None or False, otherwise unicode string)
        * string_types (replacement for basestring)
        """
        return ast.parse(dedent("""
            from collections import OrderedDict
            from odoo.tools.pycompat import to_text, string_types
            from odoo.addons.base.ir.ir_qweb.qweb import escape, foreach_iterator
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
            args=arguments(args=[
                arg(arg='self', annotation=None),
                arg(arg='append', annotation=None),
                arg(arg='values', annotation=None),
                arg(arg='options', annotation=None),
                arg(arg='log', annotation=None),
            ], defaults=[], vararg=None, kwarg=None, kwonlyargs=[], kw_defaults=[]),
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
                            comparators=[ast.Name(id='None', ctx=ast.Load())]
                        ),
                        ast.Compare(
                            left=ast.Name(id='content', ctx=ast.Load()),
                            ops=[ast.IsNot()],
                            comparators=[ast.Name(id='False', ctx=ast.Load())]
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
        if self._is_static_node(el):
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
                                    ast.Name(id='string_types', ctx=ast.Load())
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

    def _is_static_node(self, el):
        """ Test whether the given element is purely static, i.e., does not
        require dynamic rendering for its attributes.
        """
        return not any(att.startswith('t-') for att in el.attrib)

    # compile

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

        if unqualified_el_tag == 't':
            return content
        tag = u'<%s%s' % (el_tag, u''.join([u' %s="%s"' % (name, escape(pycompat.to_text(value))) for name, value in attrib.items()]))
        if unqualified_el_tag in self._void_elements:
            return [self._append(ast.Str(tag + '/>'))] + content
        else:
            return [self._append(ast.Str(tag + '>'))] + content + [self._append(ast.Str('</%s>' % el_tag))]

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
                nodes.append((key, ast.Str(value)))
        return nodes

    def _compile_dynamic_attributes(self, el, options):
        """ Compile the dynamic attributes of the given element into a list of
        pairs (name, expression AST).

        We do not support namespaced dynamic attributes.
        """
        nodes = []
        for name, value in el.attrib.items():
            if name.startswith('t-attf-'):
                nodes.append((name[7:], self._compile_format(value)))
            elif name.startswith('t-att-'):
                nodes.append((name[6:], self._compile_expr(value)))
            elif name == 't-att':
                # self._get_dynamic_att($tag, $value, options, values)
                nodes.append(ast.Call(
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
                ))
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
                if isinstance(item, tuple):
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
                        args=[item],
                        keywords=[],
                        starargs=None, kwargs=None
                    )))

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

        body = [self._append(ast.Str(u'<%s%s' % (el_tag, u''.join([u' %s="%s"' % (name, escape(pycompat.to_text(value))) for name, value in extra_attrib.items()]))))]
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
        body = []
        varname = el.attrib.pop('t-set')
        varset = self._values_var(ast.Str(varname), ctx=ast.Store())

        if 't-value' in el.attrib:
            value = self._compile_expr(el.attrib.pop('t-value'))
        elif 't-valuef' in el.attrib:
            value = self._compile_format(el.attrib.pop('t-valuef'))
        else:
            # set the content as value
            body = self._compile_directive_content(el, options)
            if body:
                def_name = self._create_def(options, body, prefix='set', lineno=el.sourceline)
                return [
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
                ]

            else:
                value = ast.Str(u'')

        # $varset = $value
        return [ast.Assign(
            targets=[self._values_var(ast.Str(varname), ctx=ast.Store())],
            value=value
        )]

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
        el.attrib['t-if'] = _elif
        compiled = self._compile_directive_if(el, options)
        el.attrib['t-elif'] = '_t_skip_else_'
        return compiled

    def _compile_directive_if(self, el, options):
        orelse = []
        next_el = el.getnext()
        if next_el is not None and {'t-else', 't-elif'} & set(next_el.attrib):
            if el.tail and not el.tail.isspace():
                raise ValueError("Unexpected non-whitespace characters between t-if and t-else directives")
            el.tail = None
            orelse = self._compile_node(next_el, dict(options, t_if=True))
        return [
            # if $t-if:
            #    next tag directive
            # else:
            #    $t-else
            ast.If(
                test=self._compile_expr(el.attrib.pop('t-if')),
                body=self._compile_directives(el, options) or [ast.Pass()],
                orelse=orelse
            )
        ]

    def _compile_directive_groups(self, el, options):
        return [
            # if self.user_has_groups($groups):
            #    next tag directive
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
                body=self._compile_directives(el, options) or [ast.Pass()],
                orelse=[]
            )
        ]

    def _compile_directive_foreach(self, el, options):
        expr = self._compile_expr(el.attrib.pop('t-foreach'))
        varname = el.attrib.pop('t-as').replace('.', '_')
        values = self._make_name('values')

        # create function $foreach
        def_name = self._create_def(options, self._compile_directives(el, options), prefix='foreach', lineno=el.sourceline)

        # for x in foreach_iterator(values, $expr, $varname):
        #     $foreach(self, append, values, options)
        return [ast.For(
            target=ast.Name(id=values, ctx=ast.Store()),
            iter=ast.Call(
                func=ast.Name(id='foreach_iterator', ctx=ast.Load()),
                args=[ast.Name(id='values', ctx=ast.Load()), expr, ast.Str(varname)],
                keywords=[], starargs=None, kwargs=None
            ),
            body=[ast.Expr(self._call_def(def_name, values=values))],
            orelse=[]
        )]

    def _compile_tail(self, el):
        return el.tail is not None and [self._append(ast.Str(pycompat.to_text(el.tail)))] or []

    def _compile_directive_esc(self, el, options):
        field_options = self._compile_widget_options(el, 'esc')
        content = self._compile_widget(el, el.attrib.pop('t-esc'), field_options)
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
        return content + self._compile_widget_value(el, options)

    def _compile_directive_raw(self, el, options):
        field_options = self._compile_widget_options(el, 'raw')
        content = self._compile_widget(el, el.attrib.pop('t-raw'), field_options)
        return content + self._compile_widget_value(el, options)

    # escape attribute is deprecated and will remove after v11
    def _compile_widget(self, el, expression, field_options, escape=None):
        if field_options:
            return [
                # value = t-(esc|raw)
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
                            field_options and self._compile_expr(field_options) or ast.Dict(keys=[], values=[]),
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
                    ast.Name(id='None', ctx=ast.Load()),
                ], ctx=ast.Load())
            )
        ]

    # for backward compatibility to remove after v10
    def _compile_widget_options(self, el, directive_type):
        return el.attrib.pop('t-options', None)
    # end backward

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
        field_options = self._compile_widget_options(el, 'field')
        record, field_name = expression.rsplit('.', 1)

        return [
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
                        field_options and self._compile_expr(field_options) or ast.Dict(keys=[], values=[]),
                        ast.Name(id='options', ctx=ast.Load()),
                        ast.Name(id='values', ctx=ast.Load()),
                    ],
                    keywords=[], starargs=None, kwargs=None
                )
            )
        ] + self._compile_widget_value(el, options)

    def _compile_widget_value(self, el, options):
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

        if nsmap or call_options:
            # copy the original dict of options to pass to the callee
            name_options = self._make_name('options')
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
                    ))
                ])

            if nsmap:
                # update this dict with the current nsmap so that the callee know
                # if he outputting the xmlns attributes is relevenat or not

                # make the nsmap an ast dict
                keys = []
                values = []
                for key, value in options['nsmap'].items():
                    if isinstance(key, pycompat.string_types):
                        keys.append(ast.Str(s=key))
                    elif key is None:
                        keys.append(ast.Name(id='None', ctx=ast.Load()))
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
        else:
            name_options = 'options'

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
        return content

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
            # values.get(0) and u''.join(values[0])
            return ast.BoolOp(
                    op=ast.And(),
                    values=[
                        ast.Call(
                            func=ast.Attribute(
                                value=ast.Name(id='values', ctx=ast.Load()),
                                attr='get',
                                ctx=ast.Load()
                            ),
                            args=[ast.Num(0)], keywords=[],
                            starargs=None, kwargs=None
                        ),
                        ast.Call(
                            func=ast.Attribute(
                                value=ast.Str(u''),
                                attr='join',
                                ctx=ast.Load()
                            ),
                            args=[
                                self._values_var(ast.Num(0), ctx=ast.Load())
                            ],
                            keywords=[], starargs=None, kwargs=None
                        )
                    ]
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
                elts.append(ast.Str(literal if isinstance(literal, pycompat.text_type) else literal.decode('utf-8')))

            expr = m.group(1) or m.group(2)
            elts.append(self._compile_strexpr(expr))
            base_idx = m.end()
        # string past last regex match
        literal = f[base_idx:]
        if literal:
            elts.append(ast.Str(literal if isinstance(literal, pycompat.text_type) else literal.decode('utf-8')))

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
