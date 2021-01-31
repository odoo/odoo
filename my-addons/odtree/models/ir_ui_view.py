# -*- coding: utf-8 -*-
##############################################################################
#
#    odtree
#    author:15251908@qq.com (openliu)
#    license:'LGPL-3
#
##############################################################################

import logging
import os

from lxml import etree

from odoo import models, tools
from odoo.tools import view_validation
from odoo.tools.view_validation import _relaxng_cache

_logger = logging.getLogger(__name__)


def relaxng_odtree(view_type):
    """ Return a validator for the given view type, or None. """
    if view_type not in _relaxng_cache:
        if (view_type == 'tree'):
            folder='odtree'
        else:
            folder='base'
        with tools.file_open(os.path.join(folder, 'rng', '%s_view.rng' % view_type)) as frng:
            try:
                relaxng_doc = etree.parse(frng)
                _relaxng_cache[view_type] = etree.RelaxNG(relaxng_doc)
            except Exception:
                _logger.exception('Failed to load RelaxNG XML schema for views validation')
                _relaxng_cache[view_type] = None
    return _relaxng_cache[view_type]


class View(models.Model):
    _inherit = 'ir.ui.view'

    def __init__(self, *args, **kwargs):
        super(View, self).__init__(*args, **kwargs)
        view_validation.relaxng=relaxng_odtree