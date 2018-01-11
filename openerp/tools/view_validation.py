""" View validation code (using assertions, not the RNG schema). """

import logging

_logger = logging.getLogger(__name__)


def valid_page_in_book(arch):
    """A `page` node must be below a `book` node."""
    return not arch.xpath('//page[not(ancestor::notebook)]')


def valid_field_in_graph(arch):
    """ Children of ``graph`` can only be ``field`` """
    for child in arch.xpath('/graph/child::*'):
        if child.tag != 'field':
            return False
    return True


def valid_field_in_tree(arch):
    """ Children of ``tree`` view must be ``field`` or ``button``."""
    for child in arch.xpath('/tree/child::*'):
        if child.tag not in ('field', 'button'):
            return False
    return True


def valid_att_in_field(arch):
    """ ``field`` nodes must all have a ``@name`` """
    return not arch.xpath('//field[not(@name)]')


def valid_att_in_label(arch):
    """ ``label`` nodes must have a ``@for`` or a ``@string`` """
    return not arch.xpath('//label[not(@for or @string)]')


def valid_att_in_form(arch):
    return True


def valid_type_in_colspan(arch):
    """A `colspan` attribute must be an `integer` type."""
    for attrib in arch.xpath('//*/@colspan'):
        try:
            int(attrib)
        except:
            return False
    return True


def valid_type_in_col(arch):
    """A `col` attribute must be an `integer` type."""
    for attrib in arch.xpath('//*/@col'):
        try:
            int(attrib)
        except:
            return False
    return True


def valid_view(arch):
    if arch.tag == 'form':
        for pred in [valid_page_in_book, valid_att_in_form, valid_type_in_colspan,
                     valid_type_in_col, valid_att_in_field, valid_att_in_label]:
            if not pred(arch):
                _logger.error('Invalid XML: %s', pred.__doc__)
                return False
    elif arch.tag == 'graph':
        for pred in [valid_field_in_graph, valid_att_in_field]:
            if not pred(arch):
                _logger.error('Invalid XML: %s', pred.__doc__)
                return False
    elif arch.tag == 'tree':
        for pred in [valid_field_in_tree, valid_att_in_field]:
            if not pred(arch):
                _logger.error('Invalid XML: %s', pred.__doc__)
                return False
    return True
