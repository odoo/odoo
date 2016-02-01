# -*- coding: utf-8 -*-
# Copyright: 2014 - OpenERP S.A. <http://openerp.com>
import types
import logging
from importlib import import_module

_logger = logging.getLogger(__name__)


def post_mortem(config, info):
    if config['debug_mode'] and isinstance(info[2], types.TracebackType):
        try:
            debugger = import_module(config["debugger"])
        except ImportError:
            _logger.warning(
                "Cannot locate debugger %s, falling back to pdb",
                config["debugger"])
            import pdb as debugger
        debugger.post_mortem(info[2])
