""" View validation code (using assertions, not the RNG schema). """

import collections
import logging
import os

from lxml import etree
from odoo import tools

_logger = logging.getLogger(__name__)


_validators = collections.defaultdict(list)
_relaxng_cache = {}

def valid_view(arch):
    for pred in _validators[arch.tag]:
        if not pred(arch):
            _logger.error("Invalid XML: %s", pred.__doc__)
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


@validate('calendar', 'diagram', 'gantt', 'graph', 'pivot', 'search', 'tree')
def schema_valid(arch):
    """ Get RNG validator and validate RNG file."""
    validator = relaxng(arch.tag)
    if validator and not validator.validate(arch):
        result = True
        for error in validator.error_log:
            _logger.error(tools.ustr(error))
            result = False
        return result
    return True

@validate('form')
def valid_page_in_book(arch):
    """A `page` node must be below a `notebook` node."""
    return not arch.xpath('//page[not(ancestor::notebook)]')


@validate('graph')
def valid_field_in_graph(arch):
    """ Children of ``graph`` can only be ``field`` """
    return all(
        child.tag == 'field'
        for child in arch.xpath('/graph/*')
    )


@validate('tree')
def valid_field_in_tree(arch):
    """ Children of ``tree`` view must be ``field`` or ``button``."""
    return all(
        child.tag in ('field', 'button')
        for child in arch.xpath('/tree/*')
    )


@validate('form', 'graph', 'tree')
def valid_att_in_field(arch):
    """ ``field`` nodes must all have a ``@name`` """
    return not arch.xpath('//field[not(@name)]')


@validate('form')
def valid_att_in_label(arch):
    """ ``label`` nodes must have a ``@for`` or a ``@string`` """
    return not arch.xpath('//label[not(@for or @string)]')


@validate('form')
def valid_att_in_form(arch):
    return True


@validate('form')
def valid_type_in_colspan(arch):
    """A `colspan` attribute must be an `integer` type."""
    return all(
        attrib.isdigit()
        for attrib in arch.xpath('//@colspan')
    )


@validate('form')
def valid_type_in_col(arch):
    """A `col` attribute must be an `integer` type."""
    return all(
        attrib.isdigit()
        for attrib in arch.xpath('//@col')
    )
