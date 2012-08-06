""" View validation code (using assertions, not the RNG schema). """

import logging

_logger = logging.getLogger(__name__)


def valid_page_in_book(arch):
    """A `page` node must be below a `book` node."""
    return not arch.xpath('//page[not(ancestor::notebook)]')


def valid_field_in_graph(arch):
    """A `field` node must be below a `graph` node."""
    return not arch.xpath('//graph[not ((field) and (@string))]')


def valid_field_in_tree(arch):
    """A `field` and `button` node must be below a `tree` node."""
    return not arch.xpath('//tree[not((field) or (button)) and (@string)]')


def valid_att_in_field(arch):
    """A `name` attribute must be in a `field` node."""
    return not arch.xpath('//field[not (@name)]')


def valid_att_in_label(arch):
    """A `for` and `string` attribute must be in a `label` node."""
    return not arch.xpath('//label[not ((@for) or (@string))]')


def valid_att_in_form(arch):
    """A `string` attribute must be in a `form` node."""
    return not arch.xpath('//form[not (@string)]')


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
        for pred in [valid_page_in_book,valid_att_in_form,valid_type_in_colspan,\
                      valid_type_in_col,valid_att_in_field,valid_att_in_label]:
            if not pred(arch):
                _logger.error('Invalid XML: %s', pred.__doc__)
                return False
    elif arch.tag == 'graph':
        for pred in [valid_field_in_graph,valid_type_in_colspan,valid_type_in_col,\
                      valid_att_in_field,valid_att_in_label]:
            if not pred(arch):
                _logger.error('Invalid XML: %s', pred.__doc__)
                return False
    elif arch.tag == 'tree':
        for pred in [valid_field_in_tree,valid_type_in_colspan,valid_type_in_col,\
                     valid_att_in_field,valid_att_in_label]:
            if not pred(arch):
                _logger.error('Invalid XML: %s', pred.__doc__)
                return False
    return True
