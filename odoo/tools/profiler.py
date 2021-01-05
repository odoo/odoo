# -*- coding: utf-8 -*-
import inspect
import json
import logging
import sys
import time
import threading
import traceback
from decorator import decorator

import odoo

from odoo import fields

_logger = logging.getLogger(__name__)

#TOFIX
# Buttons ?
# Stroring speedscope in binary field is painfull
#    cannot be easily filed without an env, (tests, loading, request)
#    difference between storing it in file (speedscope compatible) and database
#    -> difficult to optionnaly generate speedscope on the fly


class _LogTracer(object):
    def __init__(self, whitelist=None, blacklist=None, files=None, deep=False):
        self.profiles = {}
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
            return self.tracer

        in_self = frame.f_locals['self']

        if not isinstance(in_self, odoo.models.BaseModel):
            return self.tracer

        model = getattr(in_self, '_name', None)

        if self.whitelist and model not in self.whitelist:
            return self.tracer
        if model in self.blacklist and self.first_frame != frame.f_code:
            return self.tracer

        if frame.f_code not in self.profiles:
            try:
                lines, firstline = inspect.getsourcelines(frame)
                self.profiles[frame.f_code] = {
                    'model': model,
                    'filename': frame.f_code.co_filename,
                    'firstline': firstline,
                    'code': lines,
                    'calls': [],
                    'nb': 0,
                }
            except Exception:
                return
        codeProfile = self.profiles[frame.f_code]

        if not frame.f_lineno:
            codeProfile['nb'] += 1

        cr = getattr(in_self, '_cr', None)
        codeProfile['calls'].append({
            'event': event,
            'lineno': frame.f_lineno,
            'queries': cr and cr.sql_log_count,
            'time': time.time(),
            'callno': codeProfile['nb'],
        })

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
            v['report'] = {}
            l = len(v['calls'])
            for k, call in enumerate(v['calls']):
                if k+1 >= l:
                    continue

                if call['lineno'] not in v['report']:
                    v['report'][call['lineno']] = {
                        'nb_queries': 0,
                        'delay': 0,
                        'nb': 0,
                    }
                v['report'][call['lineno']]['nb'] += 1

                n = k+1
                while k+1 <= l and v['calls'][k+1]['callno'] != call['callno']:
                    n += 1
                if n >= l:
                    continue
                next_call = v['calls'][n]
                if next_call['queries'] is not None:
                    v['report'][call['lineno']]['nb_queries'] += next_call['queries'] - call.get('queries', 0)
                v['report'][call['lineno']]['delay'] += next_call['time'] - call['time']

            queries = 0
            delay = 0
            for call in v['report'].values():
                queries += call['nb_queries']
                delay += call['delay']

            if minimum_time and minimum_time > delay*1000:
                continue
            if minimum_queries and minimum_queries > queries:
                continue

            # todo: no color if output in a file
            log.append("\033[1;33m%s %s--------------------- %s, %s\033[1;0m\n\n" % (v['model'] or '', '-' * (15-len(v['model'] or '')), v['filename'], v['firstline']))
            for lineno, line in enumerate(v['code']):
                if (lineno + v['firstline']) in v['report']:
                    data = v['report'][lineno + v['firstline']]
                    log.append("%-10s%-10s%-10s%s" % (
                        str(data['nb']) if 'nb_queries' in data else '.',
                        str(data.get('nb_queries', '')),
                        str(round(data['delay']*100000)/100) if 'delay' in data else '',
                        line[:-1]))
                else:
                    log.append(" " * 30)
                    log.append(line[:-1])
                log.append('\n')

            log.append("\nTotal:\n%-10s%-10d%-10s\n\n" % (
                        str(data['nb']),
                        queries,
                        str(round(delay*100000)/100)))

        _logger.info(''.join(log))

        return result

    if not method:
        return lambda method: decorator(_odooProfile, method)

    wrapper = decorator(_odooProfile, method)
    return wrapper

def _format_stack(stack):
    return [list(frame) for frame in stack]


def get_current_frame(thread):
    frame = sys._current_frames()[thread.ident]
    while frame.f_code.co_filename == __file__:
        frame = frame.f_back
    return frame
    
class Recorder():
    """
    Generic recorder to be inherited.
    Defines default behaviours to create an entry and output result to database or a file
    """
    def __init__(self):
        # todo move all of this in Profiler class
        self.result = []
        self.profiler = None

    def _format_frame(self, frame):
        co = frame.f_code
        return (co.co_filename, frame.f_lineno, co.co_name, '')

    def _get_stack_trace(self, frame=None):
        stack = []
        frame = frame or get_current_frame(self.profiler.init_thread)
        while frame is not None and frame != self.profiler.init_frame:
            stack.append(self._format_frame(frame))
            frame = frame.f_back
        return stack

    def _make_entry(self, frame=None):
        t0 = time.time()
        entry = {
            'stack': self._get_stack_trace(frame),
            'context': dict(getattr(self.profiler.init_thread, 'exec_context', {})),
            'start': t0,
        }
        self.result.append(entry)
        return entry

    def _start(self):
        pass

    def _stop(self):
        pass

    def _post_process(self):
        """
        Postprocess result after execution in order to optimise _make_entry
        this is quite tricky since keeping frames only doesn't really work: lineo may change during execution.
        This can reverse the stack and may store the corresponding line in file (heaviest part of extract_stack)
        """
        for entry in self.result:
            entry['stack'] = list(reversed(entry['stack'])) # inspect.getsource(co)

    def _to_field(self):
        return self.result

    def _to_file(self):
        return {
            'init_stack_trace': _format_stack(self.profiler.init_stack_trace),
            'init_stack_trace_level': self.profiler.init_stack_trace_level,
            'init_thread': self.profiler.init_thread.ident,
            'result': self.result,
            'record_type': type(self).__name__,
        }

class SQLRecorder(Recorder):
    """
    Saves all executed queries in the current thread with the call stack
    """
    _row = 'sql'

    def __init__(self):
        super().__init__()
        def hook(cr, query, params, query_start, query_time):
            self._make_entry().update({
                'query': query,
                'formated_query': cr._format(query, params),
                'start': query_start,
                'time': query_time,
            })
        self.hook = hook

    def _start(self):
        init_thread = self.profiler.init_thread
        if not hasattr(init_thread, 'query_hooks'):
            init_thread.query_hooks = []
        if self.hook in init_thread.query_hooks:
            _logger.warning('record_queries recursive call')
        else:
            init_thread.query_hooks.append(self.hook)

    def _stop(self):
        self.profiler.init_thread.query_hooks.remove(self.hook)

class TracesAsyncRecorder(Recorder):
    """
    Record execution frames asynchronously every `interval` seconds.
    """
    _row = 'traces_async'

    def __init__(self, interval=0.001):
        super().__init__()
        self.active = False
        self.stop_event = threading.Event()
        self.frame_interval = interval
        self.profiler_thread = threading.Thread(target=self.run)

    def run(self):
        self.active = True
        while self.active: # maybe add a check on parent_thread state?
            self._make_entry()
            self.stop_event.wait(self.frame_interval)
        self.result.append({'stack':[], 'start': time.time()})  # add final end frame

    def _stop(self):
        self.active = False
        self.stop_event.set()
        self.profiler_thread.join()

    def _start(self):
        self.profiler_thread.start()


class TracesSyncRecorder(Recorder):
    """
    Record complete execution synchronously.
    --limit-memory-hard may need to be increased
    TODO this could be higly optimized by storing in/out instead of recovering full stack
    """
    _row = 'traces_sync'

    def _start(self):
        def record(_frame, event, _arg=None):
            if event == 'line':
                return
            self._make_entry(_frame).update({'event': event, 'frame': self._format_frame(_frame)})
            # TODO fix wrong lineo
            return record
        sys.settrace(record)

    def _stop(self):
        sys.settrace(None)

    def _get_stack_trace(self, frame=None):
        return None  # getting stack trace is expensive. Sync recorder only saves top frame and event at each call and can recompute complete stack at the end

    def _post_process(self):
        # transform evented to stacks.
        # This processing could be avoided since speedscope will transform that back to evented anyway, but it is actually simpler to integrate
        # to current speedscope logic, especially when mixed with sql recorder. Il is still a possible improvement to save this as evented and manage it later.
        current_stack = []
        for entry in self.result:
            frame = entry.pop('frame')
            event = entry.pop('event')
            if event == 'call': # todo update parent lineo and info
                current_stack.append(frame)
            if event == 'return':
                current_stack.pop()
            entry['stack'] = current_stack[:]


class ExecutionContext():
    """
    Add some context on thread at current call stack level.
    This context stored by recorder beside stack and is used by SpeedscopeResult
    to add a level to the stack with this information.
    """
    def __init__(self, context):
        self.init_stack_trace_level = len(traceback.extract_stack())
        self.context = context

    def __enter__(self):
        current_thread = threading.current_thread()
        if not hasattr(current_thread, 'exec_context'):  # may need a lock
            current_thread.exec_context = {}
        current_thread.exec_context[self.init_stack_trace_level] = self.context

    def __exit__(self, *_args):
        threading.current_thread().exec_context.pop(self.init_stack_trace_level)


class Profiler():
    """
    Context manager to use to start the recording of some execution.
    Will save sql and async stack trace by default
    """
    def __init__(self, db=True, cr=False, path=False, sql=True, traces=True, sync=False, interval=0.001, recorders=None, profile_session_id=False, description=False):
        self.cr = None
        self.start = 0
        self.duration = 0
        self.path = path
        self.profile_session_id = profile_session_id
        self.description = description
        self.profile_execution_id = False
        self.init_frame = None
        self.init_stack_trace = None
        self.init_stack_trace_level = None
        self.init_thread = None
        if cr:
            self.cr = cr
        else:
            if db is True:
                db = '' # todo guess db
                raise NotImplementedError()
            if db:
                self.cr = odoo.sql_db.db_connect(db).cursor()

        if recorders:
            self.recorders = recorders
        else:
            self.recorders = []
            if sql:
                self.recorders.append(SQLRecorder())
            if traces:
                if sync:
                    self.recorders.append(TracesSyncRecorder())
                else:
                    self.recorders.append(TracesAsyncRecorder(interval=interval))
        # self.result = {}

    def _make_ir_profile_execution(self):
        if self.cr and self.profile_session_id:
            self.cr.execute("""
                INSERT INTO 
                    ir_profile_execution(description, profile_session_id, create_date) 
                VALUES 
                    (%s, %s, %s)
                RETURNING id
            """, [
                self.description,
                self.profile_session_id,
                fields.Datetime.now()
            ])
            self.profile_execution_id = self.cr.fetchone()[0]

    def __enter__(self):
        self.init_thread = threading.current_thread()
        self.init_frame = get_current_frame(self.init_thread)
        self.init_stack_trace = traceback.extract_stack()[:-1]  # TODO smarter removal of profiler.py frames
        self.init_stack_trace_level = len(self.init_stack_trace)
        if self.cr:
            self.cr.__enter__()
            self._make_ir_profile_execution()

        self.start = time.time()
        for recorder in self.recorders:
            recorder.profiler = self
            recorder._start()
        return self

    def __exit__(self, *args):
        try:
            for recorder in self.recorders:
                recorder._stop()
            self.duration = time.time() - self.start

            for recorder in self.recorders:
                recorder._post_process()

            if self.path:
                for recorder in self.recorders:
                    row = recorder._row
                    path = '%s_%s.json' % (self.path, row)
                    _logger.info('saving record to %s', path)
                    with open(path, 'w') as f:
                        json.dump(recorder._to_file(), f, indent=4)

            if self.cr:
                if self.profile_execution_id:
                    self.cr.execute(
                        """
                            UPDATE ir_profile_execution
                            SET init_stack_trace = %s, duration = %s
                            WHERE id = %s
                        """,
                        [
                            json.dumps(_format_stack(self.init_stack_trace)),
                            self.duration,
                            self.profile_execution_id
                        ])

                    for recorder in self.recorders:
                        row = recorder._row
                        self.cr.execute(
                            """
                                UPDATE ir_profile_execution
                                SET {row_name} = %s
                                WHERE id = %s
                            """.format(row_name=row),
                            [
                                json.dumps(recorder._to_field()),
                                self.profile_execution_id
                            ])
                    self.cr.commit()
        finally:
            if self.cr:
                self.cr.__exit__(*args)  # FIXME not valid if cr is given to recorder

    # generic context manager -> decorator. Remove that since Recorders need parameters?
    def __call__(self, func):
        def wrapper(*args, **kwargs):
            with self:
                return func(*args, **kwargs)
        return wrapper

def create_session_id(cr, name, user, on=None):
    session_id = False
    if not on or not hasattr(on, 'profile_session_id'):
        cr.execute(
            'INSERT INTO ir_profile_session(create_uid, create_date, name) VALUES(%s, %s, %s) RETURNING ID',
            [
                user,
                odoo.fields.Datetime.now(),
                name,
            ]
        )
        session_id = cr.fetchone()[0]
        if on:
            on.profile_session_id = session_id
    return session_id or on.profile_session_id

class TestProfiler(Profiler):
    def __init__(self, test=None, **kwargs):
        db = test.env.cr.dbname
        cr = odoo.sql_db.db_connect(db).cursor()
        user = test.env.ref('base.user_root').id
        test_method = getattr(test, '_testMethodName', 'Unknown test method')
        description = '%s %s %s' % (test_method, test.env.user.name, 'warm' if test.warm else 'cold')
        create_session_id(cr, test_method, user, on=test)
        cr.commit()
        super().__init__(description=description, **kwargs, cr=cr, profile_session_id=test.profile_session_id)


class SpeedscopeResult():
    def __init__(self, name='Speedscope', init_stack_trace=None, **profiles_raw):
        self.init_stack_trace = init_stack_trace or []
        self.init_stack_trace_level = len(self.init_stack_trace)

        self.profiles_raw = profiles_raw
        self.name = name

        self.frames_indexes = {}
        self.frame_count = 0

        for p in self.profiles_raw.values():
            for entry in p:
                if 'query' in entry:
                    entry['stack'].append((entry['query'], entry['formated_query']))

        self.profiles = []

        # process logic
        self.caller_file = None
        self.caller_lno = None

    def add_profile(self, names, complete=False, display_name=None, **params):
        frames = []
        display_name = display_name or ','.join(names)
        for name in names:
            frames += self.profiles_raw[name]
        frames.sort(key=lambda e: e['start'])
        result = self.process(frames, **params)
        start = result[0]['at']
        end = result[-1]['at']
        if complete:
            start_stack = []
            end_stack = []
            init_stack_trace_ids = []
            for frame in self.init_stack_trace:
                _logger.info(self.init_stack_trace)
                init_stack_trace_ids.append(self.get_frame_id(self.frame_desc(frame)))
            for frame_id in init_stack_trace_ids:
                start_stack.append({
                    "type": "O",
                    "frame": frame_id,
                    "at": start
                })
            for frame_id in reversed(init_stack_trace_ids):
                end_stack.append({
                    "type": "C",
                    "frame": frame_id,
                    "at": end
                })
            result = start_stack + result + end_stack

        self.profiles.append({
            "name": display_name,
            "type": "evented",
            "unit": "seconds",
            "startValue": 0,
            "endValue": end-start,
            "events": result
        })

    def make(self, activeProfileIndex=0):
        return {
            "name": self.name,
            "activeProfileIndex": activeProfileIndex,
            "$schema": "https://www.speedscope.app/file-format-schema.json",
            "shared": {
                "frames": [{
                    "name": frame[0],
                    "file": frame[1],
                    "line": frame[2]
                } for frame in self.frames_indexes]
            },
            "profiles": self.profiles,
        }

    def frame_desc(self, frame):
        if len(frame) == 4:
            (file_path, lno, method, line) = frame
            line = '' # TODO fix line
            frame = (
                method,
                ("called at %s (%s)" % (self.caller_file, line)) if self.caller_file else '',
                self.caller_lno or '',
            )
            self.caller_file = file_path
            self.caller_lno = lno
            return frame
        else: # query
            (query, formated_query) = frame
            return (
                ('sql(%s%s)' % (query[:150], "..." if len(query) > 150 else '')),
                ('%s' % formated_query),
                False
            )

    def get_frame_id(self, frame_desc):
        if frame_desc not in self.frames_indexes:
            self.frames_indexes[frame_desc] = self.frame_count
            self.frame_count += 1
        return self.frames_indexes[frame_desc]

    def process(self, entry_list, continuous=True, hide_gaps=False): #  , hide_hook=False):
        time_shift = 0
        last_end = 0
        if not entry_list:
            return []
        events = []
        current_stack_ids = []
        self.caller_file = False
        self.caller_lno = False
        entry_end = False
        init_caller_file = self.caller_file # ???
        init_caller_lno = self.caller_lno

        frames_start = entry_list[0]['start']

        for entry in entry_list:
            entry_start = entry['start'] - frames_start
            entry_stack = entry['stack'] or []
            if events and events[-1]['at'] > entry_start:
                _logger.debug('Skipping concurrent entry\n %s', entry)
                continue
            entry_time = entry.get('time')
            entry_end = None if entry_time is None else entry_start + entry_time
            if hide_gaps and last_end:
                time_shift += entry_start - last_end
            entry_start = entry_start - time_shift
            last_end = entry_end
            if entry_time:
                entry_end = entry_start + entry_time
            entry_stack_ids = []
            self.caller_file = init_caller_file
            self.caller_lno = init_caller_lno
            for level, frame in enumerate(entry_stack):
                context = entry.get('context', {}).get(str(self.init_stack_trace_level+level))
                if context:
                    context_frame = (', '.join('%s=%s' % item for item in context.items()), '', '')
                    entry_stack_ids.append(self.get_frame_id(context_frame))
                entry_stack_ids.append(self.get_frame_id(self.frame_desc(frame)))

            level = -1
            for level, at_level in enumerate(zip(current_stack_ids, entry_stack_ids)):
                current, new = at_level
                if current != new:
                    break
            else:
                level += 1

            for frame in reversed(current_stack_ids[level:]):
                events.append({
                    "type": "C",
                    "frame": frame,
                    "at": entry_start
                })
            for frame in entry_stack_ids[level:]:
                events.append({
                    "type": "O",
                    "frame": frame,
                    "at": entry_start
                })
            current_stack_ids = entry_stack_ids
            # for sql, manually add end: query time is more important than potential concurrent samples.
            # this is not very clean and could be done with a  frame_list processing

            # PARTIAL FIX remove additionnal hook/extract_stack from profiler
            # PARTIAL FIX  fix diff between hook and profile stack (execute line no)
            if entry_end:
                if continuous:
                    clear = current_stack_ids[-1:]  # todo add flag instead to join next stack
                    #nope, todo add time on all frame, make end and start match for profiler but keep gaps in sql in prepocessing, and check end and next start to manage continousity
                    current_stack_ids = current_stack_ids[:-1]
                else:
                    clear = current_stack_ids
                    current_stack_ids = []
                for frame in reversed(clear):
                    events.append({
                        "type": "C",
                        "frame": frame,
                        "at": entry_end
                    })
        # empty currentframe in case of missing clossing frame
        for frame in reversed(current_stack_ids):
            events.append({
                "type": "C",
                "frame": frame,
                "at": max(entry_end or 0, entry_start)
            })
        return events
