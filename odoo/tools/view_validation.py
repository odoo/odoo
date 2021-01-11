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


def check_esc_message(arch, location, interactive=False):
    """Detects likely wrong uses of t-esc to create messages"""
    # TODO t-raw and <field> could also be wrongly used in similar ways
    # TODO replace white list by detection of "non-xml"
    LOCATION_WHITE_LIST = [
        'im_livechat.loader',
        'label_barcode_product_product_view',
        'label_barcode_product_template_view',
        'label_lot_template_view_expiry',
        'label_package_template_view',
        'label_picking_type_view',
        'label_product_packaging_view',
        'label_product_product_view',
        'label_product_template_view',
        'label_production_view',
        'label_transfer_template_view_zpl',
        'styles_company_report',
        'website.robots',
    ]
    INLINE_TAGS = ['t', 'span', 'small', 'strong', 'i', 'img', 'a']

    if location in LOCATION_WHITE_LIST or location.split('.')[-1] in LOCATION_WHITE_LIST:
        return

    def get_text(node, is_forward):
        result = []
        while node is not None and (node.tag is None or node.tag in INLINE_TAGS):
            if not is_forward and node.tail:
                result.append(node.tail)
            text = "".join(node.itertext())
            if text:
                result.append(text)
            if is_forward and node.tail:
                result.append(node.tail)
            node = node.getnext() if is_forward else node.getprevious()
        if not is_forward:
            result.reverse()
        return " ".join(result)

    def is_text(text):
        return re.findall('[A-Za-z]+', text) if text else False

    def publish_error(node, message):
        if interactive:
            hint = "Consider setting a message pattern in a variable as a text node before using it in an expression"
            raise ValueError('On line %s: %s\n%s' % (node.sourceline, message, hint))
        else:
            _logger.warning('In %s line %s: %s' % (location, node.sourceline, message))

    for node in arch.iterfind(".//*[@t-esc]"):
        if node.tag in INLINE_TAGS:
            esc = node.get('t-esc')
            esc_filtered = re.sub("%s|%i|%.\d+f", "", esc)
            # do not consider %s, %i, %.2f as a letter
            esc_filtered = re.sub("\['.*'\]|\[\".*\"\]|\('.*'\)|\(\".*\"\)", "", esc_filtered)
            # do not consider ['...'], ["..."], ('...') and ("...") as literals
            if re.match(".*'.*[A-Za-z]+.*'.*%|\".*[A-Za-z]+.*\".*%", esc_filtered):
                # does it contain a text literal use for formatting ?
                publish_error(node, "Non translated literal in t-esc: %s" % esc)
            else:
                before = get_text(node.getprevious(), False)
                if re.match(".*:\s*$", before):
                    before = ""
                tail = node.tail if node.tail else ""
                after = get_text(node.getnext(), True)
                if is_text(before) or is_text(tail) or is_text(after):
                    # is it surrounded by text literals ?
                    publish_error(node, re.sub("\s+", " ", "Text besides a t-esc: %s <t-esc:%s> %s %s" %
                                         (before, esc, tail, after)).strip())


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
