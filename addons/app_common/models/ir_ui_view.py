# -*- coding: utf-8 -*-

from odoo import api, models, tools, SUPERUSER_ID
from odoo.tools import file_path
from odoo.tools import file_open
from odoo.tools import view_validation
from odoo.tools.view_validation import _relaxng_cache, validate, _validators
from odoo.tools.safe_eval import safe_eval

from lxml import etree
import logging
_logger = logging.getLogger(__name__)

def app_relaxng(view_type):
    """ Return a validator for the given view type, or None. """
    if view_type not in _relaxng_cache:
        # tree, search 特殊
        if view_type in ['list', 'search']:
            _file = file_path('app_common/rng/%s_view.rng' % view_type)
        else:
            _file = file_path('base/rng/%s_view.rng' % view_type)
        with tools.file_open(_file) as frng:
            try:
                relaxng_doc = etree.parse(frng)
                _relaxng_cache[view_type] = etree.RelaxNG(relaxng_doc)
            except Exception as e:
                _logger.error('You can Ignore this. Failed to load RelaxNG XML schema for views validation: %s' % e)
                _relaxng_cache[view_type] = None
    return _relaxng_cache[view_type]

view_validation.relaxng = app_relaxng
