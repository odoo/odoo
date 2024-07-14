# -*- coding: utf-8 -*-
import logging
import os

from lxml import etree

from odoo.loglevels import ustr
from odoo.tools import misc, view_validation

_logger = logging.getLogger(__name__)

_grid_validator = None


@view_validation.validate('grid')
def schema_grid(arch, **kwargs):
    """ Check the grid view against its schema

    :type arch: etree._Element
    """
    global _grid_validator

    if _grid_validator is None:
        with misc.file_open(os.path.join('web_grid', 'views', 'grid.rng')) as f:
            _grid_validator = etree.RelaxNG(etree.parse(f))

    if _grid_validator.validate(arch):
        return True

    for error in _grid_validator.error_log:
        _logger.error(ustr(error))
    return False


@view_validation.validate('grid')
def valid_field_types(arch, **kwargs):
    """ Each of the row, col and measure <field>s must appear once and only
    once in a grid view

    :type arch: etree._Element
    """
    types = {'col', 'measure', 'readonly'}
    for f in arch.iterdescendants('field'):
        field_type = f.get('type')
        if field_type == 'row':
            continue

        if field_type in types:
            types.remove(field_type)
        else:
            return False

    return True
