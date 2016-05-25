# -*- coding: utf-8 -*-
import ast
from collections import OrderedDict, Sized, Mapping, defaultdict
from lxml import etree, html
import re
import traceback
from itertools import count
from textwrap import dedent
from werkzeug.utils import escape
from itertools import izip, tee
import __builtin__
builtin_defaults = {name: getattr(__builtin__, name) for name in dir(__builtin__)}

try:
    import astor
except ImportError:
    astor = None

import logging
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
        names = [arg.id for arg in args.args]
        if args.vararg: names.append(args.vararg)
        if args.kwarg: names.append(args.kwarg)
        # remap defaults in case there's any
        return ast.copy_location(ast.Lambda(
            args=ast.arguments(
                args=args.args,
                defaults=map(self.visit, args.defaults),
                vararg=args.vararg,
                kwarg=args.kwarg,
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
                setattr(newnode, field, map(transformer.visit, value))
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

        super(QWebException, self).__init__(message)

    def __str__(self):
        message = "%s\n%s\n%s" % (self.error, self.stack, self.message)
        if self.name:
            message = "%s\nTemplate: %s" % (message, self.name)
        if self.code:
            message = "%s\nCompiled code:\n%s" % (message, self.code)
        if self.path:
            message = "%s\nPath: %s" % (message, self.path)
        if self.html:
            message = "%s\nNode: %s" % (message, self.html)
        return message

    def __repr__(self):
        return str(self)


import werkzeug
from werkzeug.utils import escape
# Avoid DeprecationWarning while still remaining compatible with werkzeug pre-0.9
if getattr(werkzeug, '__version__', '0.0') < '0.9.0':
    def qweb_escape(text):
        return escape(unicodifier(text), quote=True)
else:
    def qweb_escape(text):
        return escape(unicodifier(text))

def unicodifier(val):
    if val is None or val is False:
        return u''
    if isinstance(val, str):
        return val.decode('utf-8')
    return unicode(val)

def foreach_iterator(base_ctx, enum, name):
    ctx = base_ctx.copy()
    if not enum:
        return
    if isinstance(enum, int):
        enum = xrange(enum)
    size = None
    if isinstance(enum, Sized):
        ctx["%s_size" % name] = size = len(enum)
    if isinstance(enum, Mapping):
        enum = enum.iteritems()
    else:
        enum = izip(*tee(enum))
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
    for k in base_ctx.keys():
        base_ctx[k] = ctx[k]

_FORMAT_REGEX = re.compile(
    '(?:'
        # ruby-style pattern
        '#\{(.+?)\}'
    ')|(?:'
        # jinja-style pattern
        '\{\{(.+?)\}\}'
    ')')


class QWebField(object):
    def attributes(self, record, field_name, options, values=None):
        return {}
    def record_to_html(self, record, field_name, options, values=None):
        return getattr(record, field_name, None)


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
        return hash(frozenset((key, freehash(val)) for key, val in self.iteritems()))


####################################
###             QWeb             ###
####################################


class QWeb(object):

    _void_elements = frozenset([
        'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'keygen',
        'link', 'menuitem', 'meta', 'param', 'source', 'track', 'wbr'])
    _name_gen = count()

    def render(self, template, values=None, **options):
        """
        'options' can be used by QWeb methods
        'values' is used to evaluate template values
        """
        body = []
        self.compile(template, options)(self, body.append, values)
        return u''.join(body)

    def compile(self, template, options):
        """
        Return a "qweb function"
        * parameters: ``append`` ``values``
        * use append method to add content
        """
        if options is None:
            options = {}

        _options = dict(options)
        options = frozendict(options)

        element, document = self.get_template(template, options)
        name = element.get('t-name', 'unknown')

        _options['ast_calls'] = []
        _options['root'] = element.getroottree()
        _options['last_path_node'] = None

        # generate ast

        astmod = self._base_module()
        try:
            self._call_body(_options, ['empty'], prefix='template_%s' % name.replace('.', '_'))
            _options['ast_calls'][0].body = self._compile_node(element, _options)
        except QWebException, e:
            raise e
        except Exception, e:
            path = _options['last_path_node']
            node = element.getroottree().xpath(path)
            raise QWebException("Error when compiling AST", e, path, etree.tostring(node[0]), name)
        astmod.body.extend(_options['ast_calls'])


        ast.fix_missing_locations(astmod)

        # compile ast

        try:
            # noinspection PyBroadException
            ns = {}
            eval(compile(astmod, '<template>', 'exec'), ns)
        except QWebException, e:
            raise e
        except Exception, e:
            path = _options['last_path_node']
            node = element.getroottree().xpath(path)
            raise QWebException("Error when compiling AST", e, path, node and etree.tostring(node[0]), name)

        # return the wrapped function

        def _compiled_fn(self, append, values):
            log = {'last_path_node': None}
            values.update(self.default_values())
            try:
                return ns[_options['ast_calls'][0].name](self, append, values, options, log)
            except QWebException, e:
                raise e
            except Exception, e:
                path = log['last_path_node']
                element, document = self.get_template(template, options)
                node = element.getroottree().xpath(path)
                raise QWebException("Error to render compiling AST", e, path, node and etree.tostring(node[0]), name)

        return _compiled_fn

    def default_values(self):
        """ attributes add to the values for each computed template
        """
        return {
            'True': True,
            'False': False,
            'None': None,
            'str': str,
            'unicode': unicode,
            'bool': bool,
            'int': int,
            'float': float,
            'long': long,
            'enumerate': enumerate,
            'dict': dict,
            'list': list,
            'tuple': tuple,
            'map': map,
            'abs': abs,
            'min': min,
            'max': max,
            'sum': sum,
            'reduce': reduce,
            'filter': filter,
            'round': round,
            'len': len,
            'repr': repr,
            'set': set,
            'all': all,
            'any': any,
            'ord': ord,
            'chr': chr,
            'cmp': cmp,
            'divmod': divmod,
            'isinstance': isinstance,
            'range': range,
            'xrange': xrange,
            'zip': zip,

            'format': self.format
        }

    def get_template(self, template, options):
        if isinstance(template, etree._Element):
            document = template
            template = etree.tostring(template)
        else:
            try:
                document = options.get('load', self.load)(template, options)
            except QWebException, e:
                raise e
            except Exception, e:
                raise QWebException("load could not load template", name=template)

        if document is not None:
            if isinstance(document, etree._Element):
                element = document
                document = etree.tostring(document)
            elif document.startswith("<?xml"):
                element = etree.fromstring(document)
            else:
                element = etree.parse(document).getroot()
            for node in element:
                if node.get('t-name') == template:
                    return (node, document)
            return (element, document)

        raise QWebException("Template not found", name=template)

    def load(self, template, options):
        return template

    # public method for template dynamic values

    def format(self, value, formating, *args, **kwargs):
        format = getattr(self, '_format_func_%s' % formating, None)
        if not format:
            raise "Unknown formating '%s'" % (formating,)
        return format(value, *args, **kwargs)

    # compute helpers

    def _base_module(self):
        """ module base supporting qweb template functions (provides basic
        imports and utilities)
        Currently provides:
        * collections
        * itertools
        Define:
        * qweb_escape
        * unicodifier (empty string for a None or False, otherwise unicode string)
        """

        return ast.parse(dedent("""
            from collections import OrderedDict
            import itertools
            from itertools import repeat, imap
            from openerp.addons.base.ir.ir_qweb.qweb import qweb_escape, unicodifier, foreach_iterator
            """))

    def _call_body(self, options, body, append='append', values='values', prefix='fn', lineno=None):
        """
        If ``body`` is non-empty, generates (and globally store) the
        corresponding function definition and returns the relevant ast.Call
        node.
        If ``body`` is empty, doesn't do anything and returns ``None``.
        Generates a "qweb function" definition:
        * takes ``append`` method and ``values`` parameter
        """
        assert body, "To create a compiled function 'body' ast list can't be empty"

        name = self._make_name(prefix)

        fn = ast.FunctionDef(
            name=name,
            args=ast.arguments(args=[
                ast.Name(id='self', ctx=ast.Param()),
                ast.Name(id='append', ctx=ast.Param()),
                ast.Name(id='values', ctx=ast.Param()),
                ast.Name(id='options', ctx=ast.Param()),
                ast.Name(id='log', ctx=ast.Param()),
            ], defaults=[], vararg=None, kwarg=None),
            body=body or [ast.Return()],
            decorator_list=[])
        if lineno is not None:
            fn.lineno = lineno

        options['ast_calls'].append(fn)

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
        assert isinstance(item, ast.expr) or isinstance(item, ast.Expr)
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
                body=body,
                # append(body default value)
                orelse=orelse,
            )

    def _make_name(self, prefix='var'):
        return "%s_%s" % (prefix, next(self._name_gen))

    def _compile_node(self, el, options):
        """
        :return ast list
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
            if not compile_handler:
                continue
            return body + compile_handler(el, options)
        if directives:
            raise "Unknown directive '%s' on %s" % ("', '".join(directives), etree.tostring(el))

        return body + self._compile_directive_content(el, options)

    def _values_var(self, varname, ctx):
        return ast.Subscript(
            value=ast.Name(id='values', ctx=ast.Load()),
            slice=ast.Index(varname),
            ctx=ctx
        )

    # order and ignore

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
            'groups', 'foreach', 'if', 'else',
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
            't-name', 't-field-options', 't-call-options'
            't-as''t-value', 't-valuef', 't-ignore',
            't-js', 't-css', 't-async', 't-placeholder',
        }

    # compile directives

    def _serialize_static_attributes(self, el, options):
        nodes = []
        for key, value in el.attrib.iteritems():
            if not key.startswith('t-'):
                nodes.append((key, ast.Str(value)))
        return nodes

    def _compile_dynamic_attributes(self, el, options):
        nodes = []
        for name, value in el.attrib.iteritems():
            if name.startswith('t-attf-'):
                nodes.append((name[7:], self._compile_format(value)))
            elif name.startswith('t-att-'):
                nodes.append((name[6:], self._compile_expr(value)))
            elif name == 't-att':
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

            items = self._serialize_static_attributes(el, options) + self._compile_dynamic_attributes(el, options)
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
            #         append(u' ')
            #         append(name)
            #         append(u'="')
            #         append(qweb_escape(value))
            #         append(u'"')
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
                            func=ast.Name(id='qweb_escape', ctx=ast.Load()),
                            args=[ast.Name(id='value', ctx=ast.Load())], keywords=[],
                            starargs=None, kwargs=None
                        )),
                        self._append(ast.Str(u'"')),
                    ],
                    orelse=[]
                )],
                orelse=[]
            ))

        return body

    def _compile_tag(self, el, content, options, attr_already_created=False):
        body = [self._append(ast.Str(u'<%s' % el.tag))]
        body.extend(self._compile_all_attributes(el, options, attr_already_created))
        if el.tag in self._void_elements:
            body.append(self._append(ast.Str(u'/>')))
            body.extend(content)
        else:
            body.append(self._append(ast.Str(u'>')))
            body.extend(content)
            body.append(self._append(ast.Str(u'</%s>' % el.tag)))
        return body

    def _compile_directive_debug(self, el, options):
        debugger = el.attrib.pop('t-debug')
        body = self._compile_node(el, options)
        if options['dev_mode']:
            body = ast.parse("__import__('%s').set_trace()" % re.sub('[^a-zA-Z]', '', debugger)).body + body  # pdb, ipdb, pudb, ...
        else:
            _logger.warning("@t-debug in template is only available in dev mode options")
        return body

    def _compile_directive_tag(self, el, options):
        el.attrib.pop('t-tag', None)
        content = self._compile_node(el, options)
        if el.tag == 't':
            return content
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
                return [
                    # $varset = []
                    ast.Assign(
                        targets=[
                            self._values_var(ast.Str(varname), ctx=ast.Store())
                        ],
                        value=ast.List(elts=[], ctx=ast.Load())
                    ),
                    # set(self, $varset.append, $varset, options)
                    ast.Expr(self._call_body(options, body,
                        append=ast.Attribute(
                            value=self._values_var(ast.Str(varname), ctx=ast.Load()),
                            attr='append',
                            ctx=ast.Load()
                        ),
                        prefix='set',
                        lineno=el.sourceline)
                    ),
                    # $varset = u''.join($varset)
                    ast.Assign(
                        targets=[self._values_var(ast.Str(varname), ctx=ast.Store())],
                        value=ast.Call(
                            func=ast.Attribute(value=ast.Str(u''), attr='join', ctx=ast.Load()),
                            args=[self._values_var(ast.Str(varname), ctx=ast.Load())], keywords=[],
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

    def _compile_directive_esc(self, el, options):
        return [
            # content = t-raw value
            ast.Assign(
                targets=[ast.Name(id='content', ctx=ast.Store())],
                value=self._compile_expr0(el.attrib.pop('t-esc')),
            ),
            # if content is not None: display
            self._if_content_is_not_Falsy(
                # append(escape($content))
                body=[self._append(ast.Call(
                    func=ast.Name(id='qweb_escape', ctx=ast.Load()),
                    args=[ast.Name(id='content', ctx=ast.Load())], keywords=[],
                    starargs=None, kwargs=None
                ))],
                # append(body default value)
                orelse=self._compile_directive_content(el, options),
            )
        ]

    def _compile_directive_raw(self, el, options):
        return [
            # content = t-raw value
            ast.Assign(
                targets=[ast.Name(id='content', ctx=ast.Store())],
                value=self._compile_expr0(el.attrib.pop('t-raw')),
            ),
            self._if_content_is_not_Falsy(
                # append($content)
                body=[self._append(ast.Call(
                    func=ast.Name(id='unicodifier', ctx=ast.Load()),
                    args=[ast.Name(id='content', ctx=ast.Load())], keywords=[],
                    starargs=None, kwargs=None
                ))],
                # append(body default value)
                orelse=self._compile_directive_content(el, options),
            )
        ]

    def _compile_directive_content(self, el, options):
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
                body.extend(self._compile_node(item, options))
                body.extend(self._compile_tail(item))
        return body

    def _compile_directive_else(self, el, options):
        if not options.pop('t_if', None):
            raise "t-else directive must be call by t-if directive"
        el.attrib.pop('t-else')
        return self._compile_node(el, options)

    def _compile_directive_if(self, el, options):
        orelse = []
        if el.tail and re.search(r'\S', el.tail):
            next = el.getnext()
            if next is not None and 't-else' in next.attrib:
                el.tail = None
                orelse = self._compile_node(next, dict(options, t_if=True))
                next.getparent().remove(next)
        return [
            ast.If(
                test=self._compile_expr(el.attrib.pop('t-if')),
                body=self._compile_node(el, options),
                orelse=orelse
            )
        ]

    def _compile_directive_groups(self, el, options):
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
                body=self._compile_node(el, options),
                orelse=[]
            )
        ]

    def _compile_directive_foreach(self, el, options):
        expr = self._compile_expr(el.attrib.pop('t-foreach'))
        varname = el.attrib.pop('t-as').replace('.', '_')
        values = self._make_name('values')

        # create function $foreach
        call = self._call_body(options, self._compile_node(el, options), values=values, prefix='foreach', lineno=el.sourceline)

        # for x in foreach_iterator(values, $expr, $varname):
        #     $foreach(self, append, values, options)
        return [ast.For(
            target=ast.Name(id=values, ctx=ast.Store()),
            iter=ast.Call(
                func=ast.Name(id='foreach_iterator', ctx=ast.Load()),
                args=[ast.Name(id='values', ctx=ast.Load()), expr, ast.Str(varname)],
                keywords=[], starargs=None, kwargs=None
            ),
            body=[ast.Expr(call)],
            orelse=[]
        )]

    def _compile_tail(self, el):
        return el.tail is not None and [self._append(ast.Str(unicodifier(el.tail)))] or []

    def _compile_directive_field(self, el, options):
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
        field_options = el.attrib.pop('t-field-options', None)
        record, field_name = expression.rsplit('.', 1)
        default_content = self._make_name('default_content')

        content = [
            # record
            ast.Assign(
                targets=[ast.Name(id='record', ctx=ast.Store())],
                value=self._compile_expr(record)
            )
        ]

        body = self._compile_directive_content(el, options)
        if body:
            content.extend([
                # default_content = []
                ast.Assign(
                    targets=[ast.Name(id=default_content, ctx=ast.Store())],
                    value=ast.List(elts=[], ctx=ast.Load())
                ),
                # body_call_content(self, default_content.append, values, options)
                ast.Expr(self._call_body(options,
                    body=body,
                    append=ast.Attribute(
                        value=ast.Name(id=default_content, ctx=ast.Load()),
                        attr='append',
                        ctx=ast.Load()
                    ),
                    prefix='body_call_content',
                    lineno=el.sourceline
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
            ])
        else:
            # default_content = u''
            content.append(ast.Assign(
                targets=[ast.Name(id=default_content, ctx=ast.Store())],
                value=ast.Str(u'')
            ))

        content.extend([
            # t_attrs, content = self._get_field(record, field_name, expression, field options, template options, values)
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
                        ast.Name(id=default_content, ctx=ast.Load()),
                        ast.Str(node_name),
                        field_options and self._compile_expr(field_options) or ast.Dict(keys=[], values=[]),
                        ast.Name(id='options', ctx=ast.Load()),
                        ast.Name(id='values', ctx=ast.Load()),
                    ],
                    keywords=[], starargs=None, kwargs=None
                ),
            ),

            # if content is not None: display the tag
            self._if_content_is_not_Falsy(
                body=self._compile_tag(el, [self._append(ast.Name(id='content', ctx=ast.Load()))], options, True),
                orelse=[]
            )
        ])
        return content

    def _compile_directive_call(self, el, options):
        """
        :param etree._Element el:
        :param list ast call:
        :return: new body
        :rtype: list(ast.AST)
        """
        tmpl = el.attrib.pop('t-call')
        _values = self._make_name('values_copy')
        call_options = el.attrib.pop('t-call-options', None)

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

            # call_content = []
            content.append(
                ast.Assign(
                    targets=[ast.Name(id='call_content', ctx=ast.Store())],
                    value=ast.List(elts=[], ctx=ast.Load())
                )
            )
            # body_call_content(self, call_content.append, values, options)
            content.append(
                ast.Expr(self._call_body(options,
                    body=body,
                    append=ast.Attribute(
                        value=ast.Name(id='call_content', ctx=ast.Load()),
                        attr='append',
                        ctx=ast.Load()
                    ),
                    values=_values,
                    prefix='body_call_content',
                    lineno=el.sourceline
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

        if call_options:
            name_options = self._make_name('options')
            content.extend([
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
                ),
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
                        ast.Str(str(tmpl)),
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

    def _get_field(self, record, field_name, expression, default_content, tagName, field_options, options, values):
        return (attributes, escape(unicodifier(getattr(record, field_name, default_content))))

    # compile expression

    def _compile_strexpr(self, expr):
        # ensure result is unicode
        return ast.Call(
            func=ast.Name(id='unicodifier', ctx=ast.Load()),
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
        expression ast, uses string concatenation via "+"
        """
        elts = []
        base_idx = 0
        for m in _FORMAT_REGEX.finditer(f):
            literal = f[base_idx:m.start()]
            if literal:
                elts.append(ast.Str(literal if isinstance(literal, unicode) else literal.decode('utf-8')))

            expr = m.group(1) or m.group(2)
            elts.append(self._compile_strexpr(expr))
            base_idx = m.end()
        # string past last regex match
        literal = f[base_idx:]
        if literal:
            elts.append(ast.Str(literal if isinstance(literal, unicode) else literal.decode('utf-8')))

        return reduce(lambda acc, it: ast.BinOp(
            left=acc,
            op=ast.Add(),
            right=it
        ), elts)

    def _compile_expr(self, expr):
        """ Compiles a purported Python expression to ast, and alter its variable
        references to access values data instead
        Can be overwrited to use a safe eval method
        It's unsafe, overwrited this method to use a safe code check
        """
        # string must be stripped otherwise whitespace before the start for
        # formatting purpose are going to break parse/compile
        st = ast.parse(expr.strip(), mode='eval')
        # ast.Expression().body -> expr
        return Contextifier().visit(st).body
