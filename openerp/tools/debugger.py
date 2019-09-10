# -*- coding: utf-8 -*-
# Copyright: 2014 - OpenERP S.A. <http://openerp.com>
import types

def post_mortem(config, info):
    if config['debug_mode'] and isinstance(info[2], types.TracebackType):
        import pdb
        pdb.post_mortem(info[2])
