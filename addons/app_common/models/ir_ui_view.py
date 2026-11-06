# -*- coding: utf-8 -*-

from odoo import api, models, tools, SUPERUSER_ID, _
from odoo.modules.module import get_resource_path
from odoo.tools import view_validation
from odoo.tools.view_validation import _relaxng_cache, validate, _validators
from odoo.tools.safe_eval import safe_eval

import os
from lxml import etree
import logging
_logger = logging.getLogger(__name__)

def app_relaxng(view_type):
    """ Return a validator for the given view type, or None. """
    if view_type not in _relaxng_cache:
        # tree, search 特殊
        if view_type in ['tree', 'search']:
            _file = get_resource_path('app_common', 'rng', '%s_view.rng' % view_type)
        else:
            _file = os.path.join('base', 'rng', '%s_view.rng' % view_type)
        with tools.file_open(_file) as frng:
            try:
                relaxng_doc = etree.parse(frng)
                _relaxng_cache[view_type] = etree.RelaxNG(relaxng_doc)
            except Exception:
                _logger.warning(_('You can Ignore this. Failed to load RelaxNG XML schema for views validation, file: %s' % _file))
                _relaxng_cache[view_type] = None
    return _relaxng_cache[view_type]

view_validation.relaxng = app_relaxng

class View(models.Model):
    _inherit = 'ir.ui.view'

    def __init__(self, env, ids, prefetch_ids):
        # 这里应该是无必要，但为了更安全
        super(View, self).__init__(env, ids, prefetch_ids)
        view_validation.relaxng = app_relaxng

    # todo: 有可能需要处理增加的 header等标签
    # 直接重写原生方法
    # def transfer_node_to_modifiers(node, modifiers, context=None, in_tree_view=False):
