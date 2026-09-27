""" View validation code (using assertions, not the RNG schema). """

import ast
import collections
import logging
import os
import re

import odoo.orm.domains as domains
from lxml import etree
from odoo import tools

_logger = logging.getLogger(__name__)


_validators = collections.defaultdict(list)
_relaxng_cache = {}

READONLY = re.compile(r"\breadonly\b")

# predefined symbols for evaluating attributes (invisible, readonly...)
IGNORED_IN_EXPRESSION = {
    'True', 'False', 'None',    # those are identifiers in Python 2.7
    'self',
    'uid',
    'context',
    'context_today',
    'allowed_company_ids',
    'current_company_id',
    'time',
    'datetime',
    'relativedelta',
    'current_date',
    'today',
    'now',
    'abs',
    'len',
    'bool',
    'float',
    'str',
    'unicode',
    'set',
}
DOMAIN_OPERATORS = {
    domains.DomainNot.OPERATOR,
    domains.DomainAnd.OPERATOR,
    domains.DomainOr.OPERATOR,
}


def get_domain_value_names(domain):
    """ Return all field name used by this domain
    eg: [
            ('id', 'in', [1, 2, 3]),
            ('field_a', 'in', parent.truc),
            ('field_b', 'in', context.get('b')),
            (1, '=', 1),
            bool(context.get('c')),
        ]
        returns {'id', 'field_a', 'field_b'}, {'parent', 'parent.truc', 'context'}

    :param domain: list(tuple) or str
    :return: set(str), set(str)
    """
    contextual_values = set()
    field_names = set()

    try:
        if isinstance(domain, list):
            for leaf in domain:
                if leaf in DOMAIN_OPERATORS or leaf in (True, False):
                    # "&", "|", "!", True, False
                    continue
                left, _operator, _right = leaf
                if isinstance(left, str):
                    field_names.add(left)
                elif left not in (1, 0):
                    # deprecate: True leaf and False leaf
                    raise ValueError()

        elif isinstance(domain, str):
            def extract_from_domain(ast_domain):
                if isinstance(ast_domain, ast.IfExp):
                    # [] if condition else []
                    extract_from_domain(ast_domain.body)
                    extract_from_domain(ast_domain.orelse)
                    return
                if isinstance(ast_domain, ast.BoolOp):
                    # condition and []
                    # this formating don't check returned domain syntax
                    for value in ast_domain.values:
                        if isinstance(value, (ast.List, ast.IfExp, ast.BoolOp, ast.BinOp)):
                            extract_from_domain(value)
                        else:
                            contextual_values.update(_get_expression_contextual_values(value))
                    return
                if isinstance(ast_domain, ast.BinOp):
                    # [] + []
                    # this formating don't check returned domain syntax
                    if isinstance(ast_domain.left, (ast.List, ast.IfExp, ast.BoolOp, ast.BinOp)):
                        extract_from_domain(ast_domain.left)
                    else:
                        contextual_values.update(_get_expression_contextual_values(ast_domain.left))

                    if isinstance(ast_domain.right, (ast.List, ast.IfExp, ast.BoolOp, ast.BinOp)):
                        extract_from_domain(ast_domain.right)
                    else:
                        contextual_values.update(_get_expression_contextual_values(ast_domain.right))
                    return
                for ast_item in ast_domain.elts:
                    if isinstance(ast_item, ast.Constant):
                        # "&", "|", "!", True, False
                        if ast_item.value not in DOMAIN_OPERATORS and ast_item.value not in (True, False):
                            raise ValueError()
                    elif isinstance(ast_item, (ast.List, ast.Tuple)):
                        left, _operator, right = ast_item.elts
                        contextual_values.update(_get_expression_contextual_values(right))
                        if isinstance(left, ast.Constant) and isinstance(left.value, str):
                            field_names.add(left.value)
                        elif isinstance(left, ast.Constant) and left.value in (1, 0):
                            # deprecate: True leaf (1, '=', 1) and False leaf (0, '=', 1)
                            pass
                        elif isinstance(right, ast.Constant) and right.value == 1:
                            # deprecate: True/False leaf (py expression, '=', 1)
                            contextual_values.update(_get_expression_contextual_values(left))
                        else:
                            raise ValueError()
                    else:
                        raise ValueError()

            expr = domain.strip()
            item_ast = ast.parse(f"({expr})", mode='eval').body
            if isinstance(item_ast, ast.Name):
                # domain="other_field_domain"
                contextual_values.update(_get_expression_contextual_values(item_ast))
            else:
                extract_from_domain(item_ast)

    except ValueError:
        raise ValueError("Wrong domain formatting.") from None

    value_names = set()
    for name in contextual_values:
        if name == 'parent':
            continue
        root = name.split('.')[0]
        if root not in IGNORED_IN_EXPRESSION:
            value_names.add(name if root == 'parent' else root)
    return field_names, value_names


def _get_expression_contextual_values(item_ast):
    """ Return all contextual value this ast

    eg: ast from '''(
            id in [1, 2, 3]
            and field_a in parent.truc
            and field_b in context.get('b')
            or (
                True
                and bool(context.get('c'))
            )
        )
        returns {'parent', 'parent.truc', 'context', 'bool'}

    :param item_ast: ast
    :return: set(str)
    """

    if isinstance(item_ast, ast.Constant):
        return set()
    if isinstance(item_ast, (ast.List, ast.Tuple)):
        values = set()
        for item in item_ast.elts:
            values |= _get_expression_contextual_values(item)
        return values
    if isinstance(item_ast, ast.Name):
        return {item_ast.id}
    if isinstance(item_ast, ast.Attribute):
        values = _get_expression_contextual_values(item_ast.value)
        if len(values) == 1:
            path = sorted(list(values)).pop()
            values = {f"{path}.{item_ast.attr}"}
            return values
        return values
    if isinstance(item_ast, ast.Index): # deprecated python ast class for Subscript key
        return _get_expression_contextual_values(item_ast.value)
    if isinstance(item_ast, ast.Subscript):
        values = _get_expression_contextual_values(item_ast.value)
        values |= _get_expression_contextual_values(item_ast.slice)
        return values
    if isinstance(item_ast, ast.Compare):
        values = _get_expression_contextual_values(item_ast.left)
        for sub_ast in item_ast.comparators:
            values |= _get_expression_contextual_values(sub_ast)
        return values
    if isinstance(item_ast, ast.BinOp):
        values = _get_expression_contextual_values(item_ast.left)
        values |= _get_expression_contextual_values(item_ast.right)
        return values
    if isinstance(item_ast, ast.BoolOp):
        values = set()
        for ast_value in item_ast.values:
            values |= _get_expression_contextual_values(ast_value)
        return values
    if isinstance(item_ast, ast.UnaryOp):
        return _get_expression_contextual_values(item_ast.operand)
    if isinstance(item_ast, ast.Call):
        values = _get_expression_contextual_values(item_ast.func)
        for ast_arg in item_ast.args:
            values |= _get_expression_contextual_values(ast_arg)
        return values
    if isinstance(item_ast, ast.IfExp):
        values = _get_expression_contextual_values(item_ast.test)
        values |= _get_expression_contextual_values(item_ast.body)
        values |= _get_expression_contextual_values(item_ast.orelse)
        return values
    if isinstance(item_ast, ast.Dict):
        values = set()
        for item in item_ast.keys:
            values |= _get_expression_contextual_values(item)
        for item in item_ast.values:
            values |= _get_expression_contextual_values(item)
        return values

    raise ValueError(f"Undefined item {item_ast!r}.")


def get_expression_field_names(expression):
    """ Return all field name used by this expression

    eg: expression = '''(
            id in [1, 2, 3]
            and field_a in parent.truc.id
            and field_b in context.get('b')
            or (True and bool(context.get('c')))
        )
        returns {'parent', 'parent.truc', 'parent.truc.id', 'context', 'context.get'}

    :param expression: str
    :param ignored: set contains the value name to ignore.
                    Add '.' to ignore attributes (eg: {'parent.'} will
                    ignore 'parent.truc' and 'parent.truc.id')
    :return: set(str)
    """
    if not expression:
        return set()
    item_ast = ast.parse(expression.strip(), mode='eval').body
    contextual_values = _get_expression_contextual_values(item_ast)

    value_names = set()
    for name in contextual_values:
        if name == 'parent':
            continue
        root = name.split('.')[0]
        if root not in IGNORED_IN_EXPRESSION:
            value_names.add(name if root == 'parent' else root)

    return value_names


def get_dict_asts(expr):
    """ Check that the given string or AST node represents a dict expression
    where all keys are string literals, and return it as a dict mapping string
    keys to the AST of values.
    """
    if isinstance(expr, str):
        expr = ast.parse(expr.strip(), mode='eval').body

    if not isinstance(expr, ast.Dict):
        raise ValueError("Non-dict expression")
    if not all((isinstance(key, ast.Constant) and isinstance(key.value, str)) for key in expr.keys):
        raise ValueError("Non-string literal dict key")
    return {key.value: val for key, val in zip(expr.keys, expr.values)}


def _check(condition, explanation):
    if not condition:
        raise ValueError("Expression is not a valid domain: %s" % explanation)


def valid_view(arch, **kwargs):
    for pred in _validators[arch.tag]:
        check = pred(arch, **kwargs)
        if not check:
            _logger.warning("Invalid XML: %s", pred.__doc__)
            return False
    return True


def validate(*view_types):
    """ Registers a view-validation function for the specific view types
    """
    def decorator(fn):
        for arch in view_types:
            _validators[arch].append(fn)
        return fn
    return decorator


def relaxng(view_type):
    """ Return a validator for the given view type, or None. """
    if view_type not in _relaxng_cache:
        with tools.file_open(os.path.join('base', 'rng', '%s_view.rng' % view_type)) as frng:
            try:
                relaxng_doc = etree.parse(frng)
                _relaxng_cache[view_type] = etree.RelaxNG(relaxng_doc)
            except Exception:
                _logger.exception('Failed to load RelaxNG XML schema for views validation')
                _relaxng_cache[view_type] = None
    return _relaxng_cache[view_type]


@validate('calendar', 'graph', 'pivot', 'search', 'list', 'activity')
def schema_valid(arch, **kwargs):
    """ Get RNG validator and validate RNG file."""
    validator = relaxng(arch.tag)
    if validator and not validator.validate(arch):
        for error in validator.error_log:
            _logger.warning("%s", error)
        return False
    return True
