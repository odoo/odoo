# -*- coding: utf-8 -*-
from decorator import decorator
import inspect
import logging
import sys
import time

import odoo
_logger = logging.getLogger(__name__)


class _LogTracer(object):
    def __init__(self, whitelist=None, blacklist=None, files=None, deep=False):
        self.profiles = {}
        self.lines = []
        self.whitelist = whitelist
        self.blacklist = blacklist
        self.files = files
        self.deep = deep
        self.first_frame = None

    def tracer(self, frame, event, arg):
        if not self.first_frame:
            self.first_frame = frame.f_code
        if not self.deep and self.first_frame != frame.f_code:
            return self.tracer

        if frame.f_code.co_name in ['<genexpr>', '__getattr__', '__iter__', '__init__']:
            return

        if 'self' not in frame.f_locals:
            return self.tracer

        if self.files and frame.f_code.co_filename not in self.files:
            return

        in_self = frame.f_locals['self']

        if isinstance(in_self, (odoo.sql_db.Cursor, odoo.sql_db.TestCursor, odoo.sql_db.LazyCursor)):
            return

        model = getattr(in_self, '_name', None)

        if self.whitelist and model not in self.whitelist:
            return
        if model in self.blacklist:
            return

        if frame.f_code not in self.profiles:
            try:
                lines, firstline = inspect.getsourcelines(frame)
                self.profiles[frame.f_code] = {
                    'model': model,
                    'filename': frame.f_code.co_filename,
                    'firstline': firstline,
                    'code': lines,
                    'lines': {},
                    'nb': 0,
                }
            except Exception:
                return
        codeProfile = self.profiles[frame.f_code]

        if not frame.f_lineno:
            codeProfile['nb'] += 1

        lineno = frame.f_lineno
        if event == 'return':
            lineno += 0.5

        if lineno not in codeProfile['lines']:
            codeProfile['lines'][lineno] = {
                'code': codeProfile,
                'infos': {},
                'nb': 0,
                'event': event
            }
        lineProfile = codeProfile['lines'][lineno]
        lineProfile['nb'] += 1

        cr = getattr(in_self, '_cr', None)
        lineProfile['infos'][codeProfile['nb']] = {
            'queries': cr and cr.sql_log_count,
            'time': time.time()
        }

        self.lines.append(lineProfile)

        return self.tracer

def profile(method=None, whitelist=None, blacklist=(None,), files=None,
        minimum_time=0, minimum_queries=0):
    """
        Decorate an entry point method.
        If profile is used without params, log as shallow mode else, log
        all methods for all odoo models by applying the optional filters.

        :param whitelist: None or list of model names to display in the log
                        (Default: None)
        :type whitelist: list or None
        :param files: None or list of filenames to display in the log
                        (Default: None)
        :type files: list or None
        :param list blacklist: list model names to remove from the log
                        (Default: remove non odoo model from the log: [None])
        :param int minimum_time: minimum time (ms) to display a method
                        (Default: 0)
        :param int minimum_queries: minimum sql queries to display a method
                        (Default: 0)
        
        .. code-block:: python

          from odoo.tools.profiler import profile

          class SaleOrder(models.Model):
            ...

            @api.model
            @profile                    # log only this create method
            def create(self, vals):
            ...
            @api.multi
            @profile()                  # log all methods for all odoo models
            def unlink(self):
            ...
            @profile(whitelist=['sale.order', 'ir.model.data'])
            def action_quotation_send(self):
            ...
            @profile(files=['/home/openerp/odoo/odoo/addons/sale/models/sale.py'])
            def write(self):
            ...

        NB: The use of the profiler modifies the execution time
    """

    deep = not method

    def _odooProfile(method, *args, **kwargs):
        log_tracer = _LogTracer(whitelist=whitelist, blacklist=blacklist, files=files, deep=deep)
        sys.settrace(log_tracer.tracer)
        try:
            result = method(*args, **kwargs)
        finally:
            sys.settrace(None)

        log = ["\n%-10s%-10s%s\n" % ('calls', 'queries', 'ms')]

        for v in log_tracer.profiles.values():
            sort_by_calls = {}
            for lineno in v['lines']:
                line = v['lines'][lineno]
                for n in line['infos']:
                    if n not in sort_by_calls:
                        sort_by_calls[n] = {}
                    sort_by_calls[n][lineno] = {
                        'queries': line['infos'][n]['queries'],
                        'time': line['infos'][n]['time'],
                        'line': line,
                    }
                line.pop('infos')
                line['nb_queries'] = 0
                line['delay'] = 0

            for n in sort_by_calls:
                linenos = sorted(sort_by_calls[n])
                for k, lineno in enumerate(linenos):
                    if k+1 < len(linenos):
                        line = sort_by_calls[n][lineno]
                        next_line = sort_by_calls[n][linenos[k+1]]
                        if 'nb_queries' in line['line'] and next_line['time'] - line['time'] > 0:
                            line['line']['nb_queries'] += next_line['queries'] - line['queries']
                            line['line']['delay'] += next_line['time'] - line['time']
                        else:
                            line['line'].pop('nb_queries')
                            line['line'].pop('delay')

            queries = 0
            delay = 0
            v['nb_queries'] = 0
            v['delay'] = 0
            for line in v['lines'].values():
                queries += line.get('nb_queries', 0)
                delay += line.get('delay', 0)

            if minimum_time and minimum_time > delay*1000:
                continue
            if minimum_queries and minimum_queries > queries:
                continue

            # todo: no color if output in a file
            log.append("\033[1;33m%s %s--------------------- %s, %s\033[1;0m\n\n" % (v['model'] or '', '-' * (15-len(v['model'] or '')), v['filename'], v['firstline']))
            for lineno, line in enumerate(v['code']):
                if (lineno + v['firstline']) in v['lines']:
                    data = v['lines'][lineno + v['firstline']]
                    log.append("%-10s%-10s%-10s%s" % (
                        str(data['nb']) if 'nb_queries' in data else '.',
                        str(data.get('nb_queries', '')),
                        str(round(data['delay']*100000)/100) if 'delay' in data else '',
                        line[:-1]))
                else:
                    log.append(" " * 30)
                    log.append(line[:-1])
                log.append('\n')

            log.append("%-10s%-10d%-10s\n\n" % (
                        str(data['nb']),
                        queries,
                        str(round(delay*100000)/100)))

        _logger.info(''.join(log))

        return result

    if not method:
        return lambda method: decorator(_odooProfile, method)

    wrapper = decorator(_odooProfile, method)
    return wrapper
