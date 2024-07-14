# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import os

from lxml import etree

from odoo.loglevels import ustr
from odoo.tools import misc, view_validation

_logger = logging.getLogger(__name__)

_map_view_validator = None


@view_validation.validate('map')
def schema_map_view(arch, **kwargs):
    global _map_view_validator

    if _map_view_validator is None:
        with misc.file_open(os.path.join('web_map', 'views', 'web_map.rng')) as f:
            _map_view_validator = etree.RelaxNG(etree.parse(f))

    if _map_view_validator.validate(arch):
        return True

    for error in _map_view_validator.error_log:
        _logger.error(ustr(error))
    return False
