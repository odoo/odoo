# -*- coding: utf-8 -*-
import logging
import os

from lxml import etree

from odoo.loglevels import ustr
from odoo.tools import misc, view_validation

_logger = logging.getLogger(__name__)

_activity_validator = None
@view_validation.validate('activity')
def schema_activity(arch):
    """ Check the activity view against its schema

    :type arch: etree._Element
    """
    global _activity_validator

    if _activity_validator is None:
        with misc.file_open(os.path.join('mail', 'views', 'activity.rng')) as f:
            _activity_validator = etree.RelaxNG(etree.parse(f))

    if _activity_validator.validate(arch):
        return True

    for error in _activity_validator.error_log:
        _logger.error(ustr(error))
    return False
