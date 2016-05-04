# -*- coding: utf-8 -*-

import ast
import itertools
from collections import Sized, Mapping, defaultdict
from openerp.tools import safe_eval
from odoo.exceptions import QWebException
import sys
import re


def base_module():
    """ module base supporting qweb template functions (provides basic
    imports and utilities)
    Currently provides:
    * collections
    * itertools
    * openerp.tools.html_escape as escape
    * unicodifier (empty string for a None or False, otherwise unicode string)
    """

    return ast.parse("""import __builtin__
from collections import OrderedDict
import itertools
from openerp.addons.base.ir.ir_qweb.utils import unicodifier, foreach_iterator
from openerp.tools import safe_eval, html_escape as escape
""")


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
        enum = itertools.izip(*itertools.tee(enum))
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
    # FIXME: maybe QWebContext could provide a ChainMap-style clone?
    for k in base_ctx.keys():
        base_ctx[k] = ctx[k]

def base_fn_def(body, name='fn', lineno=None):
    """ Generates a "qweb function" definition:
    * takes a single ``qwebcontext`` parameter
    * defines a local ``output`` list
    * returns ``u''.join(output)``
    The provided body should be a list of ast nodes, they will be injected
    between the initialization of ``body`` and its concatenation
    """

    body = [ast.Assign([ast.Name(id='output', ctx=ast.Store())], ast.List(elts=[], ctx=ast.Load()))] + \
            body + \
            [ast.Return(ast.Call(
                func=ast.Attribute(value=ast.Str(u''), attr='join', ctx=ast.Load()),
                args=[ast.Name(id='output', ctx=ast.Load())], keywords=[],
                starargs=None, kwargs=None
            ))]

    fn = ast.FunctionDef(
        name=name,
        args=ast.arguments(args=[
            ast.Name('self', ast.Param()),
            ast.Name('qwebcontext', ast.Param())
        ], defaults=[], vararg=None, kwarg=None),
        body=body,
        decorator_list=[])
    if lineno is not None:
        fn.lineno = lineno
    return fn

def get_attr_bool(attr, default=False):
    if attr:
        if attr is True:
            return ast.Name(id='True', ctx=ast.Load())
        attr = attr.lower()
        if attr in ('false', '0'):
            return ast.Name(id='False', ctx=ast.Load())
        elif attr in ('true', '1'):
            return ast.Name(id='True', ctx=ast.Load())
    return ast.Name(id=str(attr if attr is False else default), ctx=ast.Load())


class Contextifier(ast.NodeTransformer):
    """ For user-provided template expressions, replaces any ``name`` by
    :sampe:`qwebcontext.get('{name}')` so all variable accesses are
    performed on the qwebcontext rather than in the "native" scope
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
            # qwebcontext.get(name, getattr(__builtin__, name, None))
            ast.Call(
                func=ast.Attribute(
                    value=ast.Name(id='qwebcontext', ctx=ast.Load()),
                    attr='get',
                    ctx=ast.Load()
                ),
                args=[
                    ast.Str(node.id),
                    ast.Call(
                        func=ast.Name(id='getattr', ctx=ast.Load()),
                        args=[
                            ast.Name(id='__builtin__', ctx=ast.Load()),
                            ast.Str(node.id),
                            ast.Name(id='None', ctx=ast.Load()),
                        ], keywords=[],
                        starargs=None, kwargs=None
                    )
                ], keywords=[],
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


def compile_strexpr(expr):
    # ensure result is unicode
    return ast.Call(
        func=ast.Name(id='unicodifier', ctx=ast.Load()),
        args=[compile_expr(expr)], keywords=[],
        starargs=None, kwargs=None
    )

def compile_expr0(expr):
    if expr == "0":
        return ast.Call(
            func=ast.Attribute(
                value=ast.Name(id='qwebcontext', ctx=ast.Load()),
                attr='get',
                ctx=ast.Load()
            ),
            args=[ast.Num(0), ast.Str('')], keywords=[],
            starargs=None, kwargs=None
        )
    return compile_expr(expr)

def compile_expr(expr):
    """ Compiles a purported Python expression to ast, verifies that it's safe
    (according to safe_eval's semantics) and alter its variable references to
    access qwebcontext data instead
    """
    # string must be stripped otherwise whitespace before the start for
    # formatting purpose are going to break parse/compile
    st = ast.parse(expr.strip(), mode='eval')
    safe_eval.assert_valid_codeobj(
        safe_eval._SAFE_OPCODES,
        compile(st, '<>', 'eval'), # could be expr, but eval *should* be fine
        expr
    )

    # ast.Expression().body -> expr
    return Contextifier().visit(st).body

def compile_format(f):
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
        elts.append(compile_strexpr(expr))
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


_FORMAT_REGEX = re.compile(
    '(?:'
        # ruby-style pattern
        '#\{(.+?)\}'
    ')|(?:'
        # jinja-style pattern
        '\{\{(.+?)\}\}'
    ')')


class QWebTemplateNotFound(QWebException):
    pass


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
                root.append(deepcopy(node))
                arch = etree.tostring(root, encoding='utf-8', xml_declaration=True)
                return arch


class QWebContext(dict):
    def __init__(self, env, data, loader=None, templates=None):
        self.env = env
        self.loader = loader or (lambda name: env['ir.ui.view'].read_template(name))
        super(QWebContext, self).__init__(data)
        self['defined'] = lambda key: key in self
        self.templates = templates or {}

    # deprecated, use 'env' instead
    cr = property(lambda self: self.env.cr)
    uid = property(lambda self: self.env.uid)
    context = property(lambda self: self.env.context)

    def safe_eval(self, expr):
        locals_dict = defaultdict(lambda: None)
        locals_dict.update(self)
        locals_dict.pop('cr', None)
        locals_dict.pop('loader', None)
        return safe_eval.safe_eval(expr, None, locals_dict, nocopy=True, locals_builtins=True)

    def copy(self):
        """ Clone the current context, conserving all data and metadata
        (loader, template cache, ...)
        """
        return QWebContext(self.env, dict.copy(self),
                           loader=self.loader,
                           templates=self.templates)

    def __copy__(self):
        return self.copy()
