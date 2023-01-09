""" View validation code (using assertions, not the RNG schema). """

import ast
import collections
import logging
import os
import re

from lxml import etree
from odoo import tools

_logger = logging.getLogger(__name__)


_validators = collections.defaultdict(list)
_relaxng_cache = {}

READONLY = re.compile(r"\breadonly\b")


def _get_attrs_symbols():
    """ Return a set of predefined symbols for evaluating attrs. """
    return {
        'True', 'False', 'None',    # those are identifiers in Python 2.7
        'self',
        'id',
        'uid',
        'context',
        'context_today',
        'active_id',
        'active_ids',
        'allowed_company_ids',
        'current_company_id',
        'active_model',
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
    }


def get_variable_names(expr):
    """ Return the subexpressions of the kind "VARNAME(.ATTNAME)*" in the given
    string or AST node.
    """
    IGNORED = _get_attrs_symbols()
    names = set()

    def get_name_seq(node):
        if isinstance(node, ast.Name):
            return [node.id]
        elif isinstance(node, ast.Attribute):
            left = get_name_seq(node.value)
            return left and left + [node.attr]

    def process(node):
        seq = get_name_seq(node)
        if seq and seq[0] not in IGNORED:
            names.add('.'.join(seq))
        else:
            for child in ast.iter_child_nodes(node):
                process(child)

    if isinstance(expr, str):
        expr = ast.parse(expr.strip(), mode='eval').body
    process(expr)

    return names


def get_dict_asts(expr):
    """ Check that the given string or AST node represents a dict expression
    where all keys are string literals, and return it as a dict mapping string
    keys to the AST of values.
    """
    if isinstance(expr, str):
        expr = ast.parse(expr.strip(), mode='eval').body

    if not isinstance(expr, ast.Dict):
        raise ValueError("Non-dict expression")
    if not all(isinstance(key, ast.Str) for key in expr.keys):
        raise ValueError("Non-string literal dict key")
    return {key.s: val for key, val in zip(expr.keys, expr.values)}


def _check(condition, explanation):
    if not condition:
        raise ValueError("Expression is not a valid domain: %s" % explanation)


def get_domain_identifiers(expr):
    """ Check that the given string or AST node represents a domain expression,
    and return a pair of sets ``(fields, vars)`` where ``fields`` are the field
    names on the left-hand side of conditions, and ``vars`` are the variable
    names on the right-hand side of conditions.
    """
    if not expr:  # case of expr=""
        return (set(), set())
    if isinstance(expr, str):
        expr = ast.parse(expr.strip(), mode='eval').body

    fnames = set()
    vnames = set()

    if isinstance(expr, ast.List):
        for elem in expr.elts:
            if isinstance(elem, ast.Str):
                # note: this doesn't check the and/or structure
                _check(elem.s in ('&', '|', '!'),
                       f"logical operators should be '&', '|', or '!', found {elem.s!r}")
                continue

            if not isinstance(elem, (ast.List, ast.Tuple)):
                continue

            _check(len(elem.elts) == 3,
                   f"segments should have 3 elements, found {len(elem.elts)}")
            lhs, operator, rhs = elem.elts
            _check(isinstance(operator, ast.Str),
                   f"operator should be a string, found {type(operator).__name__}")
            if isinstance(lhs, ast.Str):
                fnames.add(lhs.s)

    vnames.update(get_variable_names(expr))

    return (fnames, vnames)


def valid_view(arch, **kwargs):
    for pred in _validators[arch.tag]:
        check = pred(arch, **kwargs)
        if not check:
            _logger.error("Invalid XML: %s", pred.__doc__)
            return False
        if check == "Warning":
            _logger.warning("Invalid XML: %s", pred.__doc__)
            return "Warning"
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


@validate('calendar', 'graph', 'pivot', 'search', 'tree', 'activity')
def schema_valid(arch, **kwargs):
    """ Get RNG validator and validate RNG file."""
    validator = relaxng(arch.tag)
    if validator and not validator.validate(arch):
        result = True
        for error in validator.error_log:
            _logger.error(tools.ustr(error))
            result = False
        return result
    return True
