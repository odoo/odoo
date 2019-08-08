# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import importlib
import logging
import types
import traceback
import psycopg2
import sys
_logger = logging.getLogger(__name__)
SUPPORTED_DEBUGGER = {'pdb', 'ipdb', 'wdb', 'pudb'}


def post_mortem(config, info):
    if config['dev_mode'] and isinstance(info[2], types.TracebackType):
        debug = next((opt for opt in config['dev_mode'] if opt in SUPPORTED_DEBUGGER), None)
        if debug:
            try:
                # Try to import the xpdb from config (pdb, ipdb, pudb, ...)
                importlib.import_module(debug).post_mortem(info[2])
            except ImportError:
                _logger.error('Error while importing %s.' % debug)

def print_sql(with_traceback = False):

    init_query = None
    call_tb_len = len(list(traceback.walk_stack(sys._getframe().f_back.f_back)))
    
    def func(cursor, query, params, *args):
        nonlocal init_query
        if init_query is None:
            init_query = cursor.sql_log_count
        query_id = cursor.sql_log_count + 1 - init_query
        print(str(query_id).center(10,'#'))

        encoding = psycopg2.extensions.encodings[cursor.connection.encoding]
        print(cursor._obj.mogrify(query, params).decode(encoding, 'replace'))

        if with_traceback:
            print(''.join(traceback.format_stack()[call_tb_len:-3]))
        print('-' * 10)
    return func