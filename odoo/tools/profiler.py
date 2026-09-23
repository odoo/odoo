import json
import logging
import sys
import threading
import tracemalloc
import types
from contextlib import ExitStack, nullcontext
from typing import TYPE_CHECKING, Any, Self

from psycopg import OperationalError

from odoo import tools
from odoo.libs.datetime import real_cpu_time, real_datetime_now, real_time
from odoo.libs.debug_log import DebugLog
from odoo.libs.gc import disabling_gc
from odoo.libs.worker_thread import current_worker_thread
from odoo.tools import SQL

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import EllipsisType, FrameType

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


def _format_frame(frame: FrameType) -> tuple[str, int, str, str]:
    code = frame.f_code
    return (code.co_filename, frame.f_lineno, code.co_name, "")


def _format_stack(stack: list[tuple[str, int, str, str]]) -> list[list[Any]]:
    return [list(frame) for frame in stack]


def get_current_frame(thread: threading.Thread | None = None) -> FrameType:
    frame: FrameType | None
    if thread and thread.ident is not None and thread.ident != threading.get_ident():
        frame = sys._current_frames()[thread.ident]
    else:
        frame = sys._getframe()
    while frame is not None and frame.f_code.co_filename == __file__:
        frame = frame.f_back
    assert frame is not None
    return frame


def _get_stack_trace(
    frame: FrameType | None,
    limit_frame: FrameType | None = None,
) -> list[tuple[str, int, str, str]]:
    stack = []
    while frame is not None and frame != limit_frame:
        stack.append(_format_frame(frame))
        frame = frame.f_back
    if frame is None and limit_frame:
        _logger.runbot("Limit frame was not found")  # type: ignore[attr-defined]
    return list(reversed(stack))


def stack_size() -> int:
    frame: FrameType | None = get_current_frame()
    size = 0
    while frame:
        size += 1
        frame = frame.f_back
    return size


def get_session_name(name: str = "") -> str:
    return f"{real_datetime_now():%Y-%m-%d %H:%M:%S} {name}"


def force_hook() -> None:
    thread = threading.current_thread()
    for func in tuple(getattr(thread, "profile_hooks", ())):
        func()


class Collector:
    name: str = ""
    _store: str | None = None
    _registry: dict[str, type[Collector]] = {}

    @classmethod
    def __init_subclass__(cls):
        if cls.name:
            cls._registry[cls.name] = cls

    @classmethod
    def prepare_collector(cls, name: str, *args: Any, **kwargs: Any) -> Collector:
        return cls._registry[name](*args, **kwargs)

    def __init__(self) -> None:
        self._processed: bool = False
        self._entries: list[dict[str, Any]] = []
        self.processed_entries: list[dict[str, Any]] = []
        self._profiler: Profiler | None = None

    @property
    def profiler(self) -> Profiler:
        if self._profiler is None:
            msg = (
                f"{type(self).__name__} has no profiler yet: a collector is "
                f"usable only once a Profiler has adopted it."
            )
            raise RuntimeError(msg)
        return self._profiler

    @profiler.setter
    def profiler(self, profiler: Profiler) -> None:
        self._profiler = profiler

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def add(
        self,
        entry: dict[str, Any] | None = None,
        frame: FrameType | None = None,
    ) -> None:
        self._entries.append(
            {
                "stack": self._get_stack_trace(frame),
                "exec_context": getattr(self.profiler.init_thread, "exec_context", ()),
                "start": real_time(),
                **(entry or {}),
            }
        )

    def progress(
        self,
        entry: dict[str, Any] | None = None,
        frame: FrameType | None = None,
    ) -> None:
        if (
            self.profiler.entry_count_limit
            and self.profiler.counter >= self.profiler.entry_count_limit
        ):
            _debug.logic(
                "profiler.entry_limit_reached",
                collector=self.name,
                limit=self.profiler.entry_count_limit,
                ending=threading.current_thread() is self.profiler.init_thread,
            )
            if threading.current_thread() is self.profiler.init_thread:
                self.profiler.end()
            return
        self.profiler.counter += 1
        self.add(entry=entry, frame=frame)

    def _get_stack_trace(
        self, frame: FrameType | None = None
    ) -> list[tuple[str, int, str, str]] | None:
        frame = frame or get_current_frame(self.profiler.init_thread)
        return _get_stack_trace(frame, self.profiler.init_frame)

    def post_process(self) -> None:
        for entry in self._entries:
            stack = entry.get("stack", [])
            self.profiler._add_file_lines(stack)

    @property
    def entries(self) -> list[dict[str, Any]]:
        if not self._processed:
            with _debug.perf(
                "profiler.post_process", collector=self.name, entries=len(self._entries)
            ):
                self.post_process()
            self.processed_entries = self._entries
            self._entries = []
            self._processed = True
        return self.processed_entries

    def summary(self) -> str:
        entries = self.processed_entries if self._processed else self._entries
        return f"{'=' * 10} {self.name} {'=' * 10} \n Entries: {len(entries)}"


class SQLCollector(Collector):
    name = "sql"

    def start(self) -> None:
        init_thread = self.profiler.init_thread
        if not hasattr(init_thread, "query_hooks"):
            init_thread.query_hooks = []
        init_thread.query_hooks.append(self.hook)

    def stop(self) -> None:
        self.profiler.init_thread.query_hooks.remove(self.hook)

    def hook(
        self,
        cr: Any,
        query: Any,
        params: Any,
        query_start: float,
        query_time: float,
    ) -> None:
        self.progress(
            {
                "query": str(query),
                "full_query": str(cr._format_statement(query, params)),
                "start": query_start,
                "time": query_time,
            }
        )

    def summary(self) -> str:
        entries = self.processed_entries if self._processed else self._entries
        total_time = sum(entry["time"] for entry in entries) or 1
        sql_entries = []
        for entry in entries:
            bar = "*" * int(entry["time"] / total_time * 100)
            sql_entries.append(
                f"\n{'-' * 100}\n{entry['time']}  {bar}\n{entry['full_query']}"
            )
        return super().summary() + "".join(sql_entries)


class _BasePeriodicCollector(Collector):
    _min_interval: float = 0.001
    _max_interval: float = 5
    _default_interval: float = 0.001

    def __init__(self, interval: float | None = None) -> None:
        super().__init__()
        self.frame_interval: float = interval or self._default_interval
        self.__thread = threading.Thread(
            target=self.run, name=f"odoo.profiler.{self.name}", daemon=True
        )
        self.last_frame: FrameType | None = None
        self._last_time: float = 0.0
        self._stop_event = threading.Event()

    def start(self) -> None:
        interval = self.profiler.params.get(f"{self.name}_interval")
        if interval:
            self.frame_interval = min(
                max(float(interval), self._min_interval), self._max_interval
            )
        init_thread = self.profiler.init_thread
        if not hasattr(init_thread, "profile_hooks"):
            init_thread.profile_hooks = []
        init_thread.profile_hooks.append(self.progress)
        self.__thread.start()
        _debug.lifecycle(
            "profiler.periodic_started",
            collector=self.name,
            interval=self.frame_interval,
            thread=self.__thread.name,
        )

    def run(self) -> None:
        self._last_time = real_time()
        while not self._stop_event.is_set():
            self.progress()
            self._stop_event.wait(self.frame_interval)

    def stop(self) -> None:
        self._stop_event.set()
        if self.__thread.is_alive() and self.__thread is not threading.current_thread():
            self.__thread.join()
        self._entries.append({"stack": [], "start": real_time()})
        self.last_frame = None
        self.profiler.init_thread.profile_hooks.remove(self.progress)
        _debug.lifecycle(
            "profiler.periodic_stopped", collector=self.name, entries=len(self._entries)
        )


class PeriodicCollector(_BasePeriodicCollector):
    name = "traces_async"

    def add(self, entry=None, frame=None):
        if self.last_frame:
            duration = real_time() - self._last_time
            if duration > self.frame_interval * 10:
                self._entries[-1]["stack"].append(
                    (
                        "profiling",
                        0,
                        "⚠ Profiler freezed for %s s" % duration,
                        "",
                    )
                )
                self.last_frame = None
        self._last_time = real_time()

        frame = frame or get_current_frame(self.profiler.init_thread)
        if frame == self.last_frame:
            return
        self.last_frame = frame
        super().add(entry=entry, frame=frame)


_lock = threading.Lock()


class MemoryCollector(_BasePeriodicCollector):
    name = "memory"
    _store = "others"
    _min_interval = 0.01
    _default_interval = 1
    _lock_acquired = False
    _owns_tracing = False

    def start(self):
        self._lock_acquired = _lock.acquire(timeout=5)
        if not self._lock_acquired:
            _logger.warning(
                "Memory collector not started: another memory collector is "
                "already active in this process"
            )
            _debug.logic("profiler.memory_collector_busy")
            return
        self._owns_tracing = not tracemalloc.is_tracing()
        _debug.logic("profiler.memory_tracing", owned=self._owns_tracing)
        try:
            if self._owns_tracing:
                tracemalloc.start()
            super().start()
        except BaseException:
            self._stop_owned_tracing()
            _lock.release()
            self._lock_acquired = False
            raise

    def add(self, entry=None, frame=None):
        self._entries.append(
            {
                "start": real_time(),
                "memory": tracemalloc.take_snapshot(),
            }
        )

    def stop(self):
        if not self._lock_acquired:
            return
        try:
            super().stop()
        finally:
            self._stop_owned_tracing()
            _lock.release()
            self._lock_acquired = False

    def _stop_owned_tracing(self) -> None:
        if self._owns_tracing:
            tracemalloc.stop()
            self._owns_tracing = False

    def post_process(self):
        for i, entry in enumerate(self._entries):
            if entry.get("memory", False):
                entry_statistics = entry["memory"].statistics("traceback")
                modified_entry_statistics = [
                    {
                        "traceback": list(statistic.traceback._frames),
                        "size": statistic.size,
                    }
                    for statistic in entry_statistics
                ]
                self._entries[i] = {
                    "memory_tracebacks": modified_entry_statistics,
                    "start": entry["start"],
                }


class SyncCollector(Collector):
    name = "traces_sync"

    def __init__(self) -> None:
        super().__init__()
        self._hook = self.hook

    def start(self):
        if (existing := sys.gettrace()) is not None:
            msg = (
                f"Cannot start SyncCollector: sys.settrace is already set to "
                f"{existing!r}. Profiling would silently disable it."
            )
            raise RuntimeError(msg)
        if self._processed:
            msg = "You cannot start SyncCollector after accessing entries."
            raise RuntimeError(msg)
        sys.settrace(self._hook)

    def stop(self):
        if sys.gettrace() is self._hook:
            sys.settrace(None)

    def hook(self, _frame, event, _arg=None):
        # the profiler's own teardown (__exit__, end, stop) runs traced
        if event == "line" or _frame.f_code.co_filename == __file__:
            return None
        entry = {"event": event, "frame": _format_frame(_frame)}
        if event == "call" and _frame.f_back:
            entry["parent_frame"] = _format_frame(_frame.f_back)
        self.progress(entry, frame=_frame)
        return self._hook

    def _get_stack_trace(self, frame=None):
        return None

    def post_process(self):
        stack: list[tuple[str, int, str, str]] = []
        for entry in self._entries:
            frame = entry.pop("frame")
            event = entry.pop("event")
            if event == "call":
                if stack:
                    stack[-1] = entry.pop("parent_frame")
                stack.append(frame)
            elif event == "return":
                stack.pop()
            entry["stack"] = stack.copy()
        super().post_process()


class QwebTracker:
    def __init__(self, view_id: int, arch: Any, cr: Any) -> None:
        current_thread = threading.current_thread()
        self.execution_context_enabled: bool | None = getattr(
            current_thread, "profiler_params", {}
        ).get("execution_context_qweb")
        self.qweb_hooks: tuple[Callable[..., None], ...] = getattr(
            current_thread, "qweb_hooks", ()
        )
        self.context_stack: list[ExecutionContext] = []
        self.cr: Any = cr
        self.view_id: int = view_id
        for hook in self.qweb_hooks:
            hook("render", self.cr.sql_log_count, view_id=view_id, arch=arch)

    def enter_directive(
        self, directive: str, attrib: dict[str, str], xpath: str
    ) -> None:
        execution_context = None
        if self.execution_context_enabled:
            directive_info: dict[str, str | None] = {}
            if ("t-" + directive) in attrib:
                directive_info["t-" + directive] = repr(attrib["t-" + directive])
            if directive == "set":
                if "t-value" in attrib:
                    directive_info["t-value"] = repr(attrib["t-value"])
                if "t-valuef" in attrib:
                    directive_info["t-valuef"] = repr(attrib["t-valuef"])

                for key, value in attrib.items():
                    if key.startswith(("t-set-", "t-setf-")):
                        directive_info[key] = repr(value)
            elif directive == "foreach":
                directive_info["t-as"] = repr(attrib["t-as"])
            elif (
                directive == "groups"
                and "groups" in attrib
                and not directive_info.get("t-groups")
            ):
                directive_info["t-groups"] = repr(attrib["groups"])
            elif directive == "att":
                for key, value in attrib.items():
                    if key.startswith(("t-att-", "t-attf-")):
                        directive_info[key] = repr(value)
            elif directive == "options":
                for key, value in attrib.items():
                    if key.startswith("t-options-"):
                        directive_info[key] = repr(value)
            elif ("t-" + directive) not in attrib:
                directive_info["t-" + directive] = None

            execution_context = tools.profiler.ExecutionContext(
                **directive_info, xpath=xpath
            )
            execution_context.__enter__()
            self.context_stack.append(execution_context)

        for hook in self.qweb_hooks:
            hook(
                "enter",
                self.cr.sql_log_count,
                view_id=self.view_id,
                xpath=xpath,
                directive=directive,
                attrib=attrib,
            )

    def leave_directive(
        self, directive: str, attrib: dict[str, str], xpath: str
    ) -> None:
        if self.execution_context_enabled:
            self.context_stack.pop().__exit__()

        for hook in self.qweb_hooks:
            hook(
                "leave",
                self.cr.sql_log_count,
                view_id=self.view_id,
                xpath=xpath,
                directive=directive,
                attrib=attrib,
            )


class QwebCollector(Collector):
    name = "qweb"

    def __init__(self):
        super().__init__()
        self.events: list[tuple[str, dict[str, Any], int, float]] = []

        def hook(event, sql_log_count, **kwargs):
            self.events.append((event, kwargs, sql_log_count, real_time()))

        self.hook = hook

    def _get_directive_profiling_name(self, directive, attrib):
        expr = ""
        if directive == "set":
            if "t-set" in attrib:
                expr = f"t-set={attrib['t-set']!r}"
                if "t-value" in attrib:
                    expr += f" t-value={attrib['t-value']!r}"
                if "t-valuef" in attrib:
                    expr += f" t-valuef={attrib['t-valuef']!r}"
            for key in attrib:
                if key.startswith(("t-set-", "t-setf-")):
                    if expr:
                        expr += " "
                    expr += f"{key}={attrib[key]!r}"
        elif directive == "foreach":
            expr = f"t-foreach={attrib['t-foreach']!r} t-as={attrib['t-as']!r}"
        elif directive == "options":
            if attrib.get("t-options"):
                expr = f"t-options={attrib['t-options']!r}"
            for key in attrib:
                if key.startswith("t-options-"):
                    expr = f"{expr}  {key}={attrib[key]!r}"
        elif directive == "att":
            for key in attrib:
                if key == "t-att" or key.startswith(("t-att-", "t-attf-")):
                    if expr:
                        expr += " "
                    expr += f"{key}={attrib[key]!r}"
        elif ("t-" + directive) in attrib:
            expr = f"t-{directive}={attrib['t-' + directive]!r}"
        else:
            expr = f"t-{directive}"

        return expr

    def start(self):
        init_thread = self.profiler.init_thread
        if not hasattr(init_thread, "qweb_hooks"):
            init_thread.qweb_hooks = []
        init_thread.qweb_hooks.append(self.hook)

    def stop(self):
        self.profiler.init_thread.qweb_hooks.remove(self.hook)

    def post_process(self):
        last_event_query = 0
        last_event_time = 0.0
        stack: list[dict[str, Any]] = []
        results: list[dict[str, Any]] = []
        archs: dict[int, Any] = {}
        for event, kwargs, sql_count, event_time in self.events:
            if event == "render":
                archs[kwargs["view_id"]] = kwargs["arch"]
                continue

            if stack:
                top = stack[-1]
                top["delay"] += event_time - last_event_time
                top["query"] += sql_count - last_event_query
            last_event_time = event_time
            last_event_query = sql_count

            directive = self._get_directive_profiling_name(
                kwargs["directive"], kwargs["attrib"]
            )
            if directive:
                if event == "enter":
                    data = {
                        "view_id": kwargs["view_id"],
                        "xpath": kwargs["xpath"],
                        "directive": directive,
                        "delay": 0,
                        "query": 0,
                    }
                    results.append(data)
                    stack.append(data)
                elif event == "leave":
                    stack.pop()
                else:
                    raise ValueError(f"unexpected qweb event {event!r}")

        self.add({"results": {"archs": archs, "data": results}})
        super().post_process()


class ExecutionContext:
    def __init__(self, **context: Any) -> None:
        self.context: dict[str, Any] = context
        self.previous_context: tuple | None = None

    def __enter__(self) -> Self:
        current_thread: Any = threading.current_thread()
        self.previous_context = getattr(current_thread, "exec_context", ())
        current_thread.exec_context = self.previous_context + (
            (stack_size(), self.context),
        )
        return self

    def __exit__(self, *_args: object) -> None:
        current_worker_thread().exec_context = self.previous_context


class Profiler:
    def __init__(
        self,
        collectors: list[str | Collector] | None = None,
        db: str | EllipsisType | None = ...,
        profile_session: str | None = None,
        description: str | None = None,
        disable_gc: bool = False,
        params: dict[str, Any] | None = None,
        log: bool = False,
    ) -> None:
        self.start_time: float = 0
        self.duration: float = 0
        self.start_cpu_time: float = 0
        self.cpu_duration: float = 0
        self.profile_session: str = profile_session or get_session_name()
        self.description: str | None = description
        self.init_frame: FrameType | None = None
        self.init_stack_trace: list[tuple[str, int, str, str]] | None = None
        self.init_thread: Any = None
        self.disable_gc: bool = disable_gc
        self.filecache: dict[str, list[str] | None] = {}
        self.params: dict[str, Any] = params or {}
        self.profile_id: int | None = None
        self.log: bool = log
        self.sub_profilers: list[Profiler] = []
        self.entry_count_limit: int = int(self.params.get("entry_count_limit", 0))
        self.done: bool = False
        self._end_lock: threading.Lock = threading.Lock()
        self.exit_stack: ExitStack = ExitStack()
        self.counter: int = 0

        if db is ...:
            db = getattr(current_worker_thread(), "dbname", None)
            if not db:
                msg = "Database name cannot be defined automaticaly. \n Please provide a valid/falsy dbname or path parameter"
                raise ValueError(msg)
        self.db: str | None = db

        if collectors is None:
            collectors = ["sql", "traces_async"]
        self.collectors: list[Collector] = []
        for collector in collectors:
            if isinstance(collector, str):
                try:
                    collector = Collector.prepare_collector(collector)
                except Exception:
                    _logger.error("Could not create collector with name %r", collector)
                    _debug.logic("profiler.collector_unknown", name=collector)
                    continue
            collector.profiler = self
            self.collectors.append(collector)

    def __enter__(self) -> Self:
        self.init_thread = threading.current_thread()
        self.init_frame = get_current_frame(self.init_thread)
        self.init_stack_trace = _get_stack_trace(self.init_frame)

        if self.description is None:
            frame = self.init_frame
            code = frame.f_code
            self.description = (
                f"{frame.f_code.co_name} ({code.co_filename}:{frame.f_lineno})"
            )
        if self.params:
            self.init_thread.profiler_params = self.params
        if self.disable_gc:
            self.exit_stack.enter_context(disabling_gc())
        # logged before the collectors start: a tracing collector would
        # otherwise record the logging call as part of the profiled code
        _debug.lifecycle(
            "profiler.starting",
            db=self.db,
            session=self.profile_session,
            description=self.description,
            collectors=[collector.name for collector in self.collectors],
            disable_gc=self.disable_gc,
        )
        self.start_time = real_time()
        self.start_cpu_time = real_cpu_time()
        started = []
        try:
            for collector in self.collectors:
                collector.start()
                started.append(collector)
        except BaseException as exc:
            _debug.logic(
                "profiler.start_rolled_back",
                session=self.profile_session,
                started=[collector.name for collector in started],
                error=type(exc).__name__,
            )
            for collector in reversed(started):
                try:
                    collector.stop()
                except Exception:
                    _logger.exception(
                        "Failed to stop collector %s during profiler start rollback",
                        collector,
                    )
            raise
        return self

    def __exit__(self, *args: object) -> None:
        self.end()

    def end(self) -> None:
        with self._end_lock:
            if self.done:
                _debug.logic("profiler.end_repeated", session=self.profile_session)
                return
            self.done = True
        try:
            for collector in self.collectors:
                try:
                    collector.stop()
                except Exception:
                    _logger.exception("Failed to stop collector %s", collector)
            self.duration = real_time() - self.start_time
            self.cpu_duration = real_cpu_time() - self.start_cpu_time
            self._add_file_lines(self.init_stack_trace)
            _debug.lifecycle(
                "profiler.ended",
                db=self.db,
                session=self.profile_session,
                duration=self.duration,
                cpu_duration=self.cpu_duration,
                entries=self.entry_count(),
            )

            if self.db:
                from odoo.db import (
                    db_connect,
                )

                with db_connect(self.db).cursor() as cr:
                    values = {
                        "name": self.description,
                        "session": self.profile_session,
                        "create_date": real_datetime_now(),
                        "init_stack_trace": json.dumps(
                            _format_stack(self.init_stack_trace or [])
                        ),
                        "duration": self.duration,
                        "cpu_duration": self.cpu_duration,
                        "entry_count": self.entry_count(),
                        "sql_count": sum(
                            len(collector.entries)
                            for collector in self.collectors
                            if collector.name == "sql"
                        ),
                    }
                    others = {}
                    for collector in self.collectors:
                        if collector.entries:
                            if collector._store == "others":
                                others[collector.name] = json.dumps(collector.entries)
                            else:
                                values[collector.name] = json.dumps(collector.entries)
                    if others:
                        values["others"] = json.dumps(others)
                    query = SQL(
                        "INSERT INTO ir_profile(%s) VALUES %s RETURNING id",
                        SQL(",").join(map(SQL.identifier, values)),
                        tuple(values.values()),
                    )
                    cr.execute(query)
                    row = cr.fetchone()
                    assert row is not None
                    self.profile_id = row[0]
                    _logger.info(
                        "ir_profile %s (%s) created",
                        self.profile_id,
                        self.profile_session,
                    )
                    _debug.lifecycle(
                        "profiler.saved",
                        db=self.db,
                        profile=self.profile_id,
                        session=self.profile_session,
                        sql_count=values["sql_count"],
                        others=sorted(others),
                    )
        except OperationalError as exc:
            _logger.exception("Could not save profile in database")
            _debug.logic(
                "profiler.save_failed",
                db=self.db,
                session=self.profile_session,
                error=type(exc).__name__,
            )
        finally:
            self.init_frame = None
            self.exit_stack.close()
            if (
                self.params
                and getattr(self.init_thread, "profiler_params", None) is self.params
            ):
                del self.init_thread.profiler_params
            if self.log:
                _logger.info(self.summary())

    def _get_cm_proxy(self) -> Nested:
        return Nested(self)

    def _add_file_lines(self, stack: list[tuple[str, int, str, str]] | None) -> None:
        if stack is None:
            return
        for index, frame in enumerate(stack):
            filename, lineno, name, line = frame
            if line != "":
                continue
            if not lineno:
                continue
            try:
                filelines = self.filecache[filename]
            except KeyError:
                try:
                    with tools.file_open(filename, filter_ext=(".py",)) as f:
                        filelines = f.readlines()
                except (
                    ValueError,
                    FileNotFoundError,
                ):
                    filelines = None
                self.filecache[filename] = filelines
            if filelines is not None and 0 < lineno <= len(filelines):
                line = filelines[lineno - 1]
                stack[index] = (filename, lineno, name, line)

    def entry_count(self) -> int:
        return sum(len(collector.entries) for collector in self.collectors)

    def summary(self) -> str:
        result = ""
        for profiler in [self, *self.sub_profilers]:
            for collector in profiler.collectors:
                result += f"\n{profiler.description}\n{collector.summary()}"
        return result


class Nested:
    def __init__(self, profiler: Profiler, context_manager: Any = None) -> None:
        self._profiler__: Profiler = profiler
        self.context_manager: Any = context_manager or nullcontext()

    def __enter__(self) -> Any:
        self._profiler__.__enter__()
        return self.context_manager.__enter__()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: types.TracebackType | None,
    ) -> bool | None:
        try:
            return self.context_manager.__exit__(exc_type, exc_value, traceback)
        finally:
            self._profiler__.__exit__(exc_type, exc_value, traceback)
