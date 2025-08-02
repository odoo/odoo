""":module: watchdog.tricks
:synopsis: Utility event handlers.
:author: yesudeep@google.com (Yesudeep Mangalapilly)
:author: contact@tiger-222.fr (Mickaël Schoentgen)

Classes
-------
.. autoclass:: Trick
   :members:
   :show-inheritance:

.. autoclass:: LoggerTrick
   :members:
   :show-inheritance:

.. autoclass:: ShellCommandTrick
   :members:
   :show-inheritance:

.. autoclass:: AutoRestartTrick
   :members:
   :show-inheritance:

"""

from __future__ import annotations

import contextlib
import functools
import logging
import os
import signal
import subprocess
import threading
import time

from watchdog.events import EVENT_TYPE_CLOSED_NO_WRITE, EVENT_TYPE_OPENED, FileSystemEvent, PatternMatchingEventHandler
from watchdog.utils import echo, platform
from watchdog.utils.event_debouncer import EventDebouncer
from watchdog.utils.process_watcher import ProcessWatcher

logger = logging.getLogger(__name__)
echo_events = functools.partial(echo.echo, write=lambda msg: logger.info(msg))


class Trick(PatternMatchingEventHandler):
    """Your tricks should subclass this class."""

    def __repr__(self) -> str:
        return f"<{type(self).__name__}>"

    @classmethod
    def generate_yaml(cls) -> str:
        return f"""- {cls.__module__}.{cls.__name__}:
  args:
  - argument1
  - argument2
  kwargs:
    patterns:
    - "*.py"
    - "*.js"
    ignore_patterns:
    - "version.py"
    ignore_directories: false
"""


class LoggerTrick(Trick):
    """A simple trick that does only logs events."""

    @echo_events
    def on_any_event(self, event: FileSystemEvent) -> None:
        pass


class ShellCommandTrick(Trick):
    """Executes shell commands in response to matched events."""

    def __init__(
        self,
        shell_command: str,
        *,
        patterns: list[str] | None = None,
        ignore_patterns: list[str] | None = None,
        ignore_directories: bool = False,
        wait_for_process: bool = False,
        drop_during_process: bool = False,
    ):
        super().__init__(
            patterns=patterns,
            ignore_patterns=ignore_patterns,
            ignore_directories=ignore_directories,
        )
        self.shell_command = shell_command
        self.wait_for_process = wait_for_process
        self.drop_during_process = drop_during_process

        self.process: subprocess.Popen[bytes] | None = None
        self._process_watchers: set[ProcessWatcher] = set()

    def on_any_event(self, event: FileSystemEvent) -> None:
        if event.event_type in {EVENT_TYPE_OPENED, EVENT_TYPE_CLOSED_NO_WRITE}:
            # FIXME: see issue #949, and find a way to better handle that scenario
            return

        from string import Template

        if self.drop_during_process and self.is_process_running():
            return

        object_type = "directory" if event.is_directory else "file"
        context = {
            "watch_src_path": event.src_path,
            "watch_dest_path": "",
            "watch_event_type": event.event_type,
            "watch_object": object_type,
        }

        if self.shell_command is None:
            if hasattr(event, "dest_path"):
                context["dest_path"] = event.dest_path
                command = 'echo "${watch_event_type} ${watch_object} from ${watch_src_path} to ${watch_dest_path}"'
            else:
                command = 'echo "${watch_event_type} ${watch_object} ${watch_src_path}"'
        else:
            if hasattr(event, "dest_path"):
                context["watch_dest_path"] = event.dest_path
            command = self.shell_command

        command = Template(command).safe_substitute(**context)
        self.process = subprocess.Popen(command, shell=True)
        if self.wait_for_process:
            self.process.wait()
        else:
            process_watcher = ProcessWatcher(self.process, None)
            self._process_watchers.add(process_watcher)
            process_watcher.process_termination_callback = functools.partial(
                self._process_watchers.discard,
                process_watcher,
            )
            process_watcher.start()

    def is_process_running(self) -> bool:
        return bool(self._process_watchers or (self.process is not None and self.process.poll() is None))


class AutoRestartTrick(Trick):
    """Starts a long-running subprocess and restarts it on matched events.

    The command parameter is a list of command arguments, such as
    `['bin/myserver', '-c', 'etc/myconfig.ini']`.

    Call `start()` after creating the Trick. Call `stop()` when stopping
    the process.
    """

    def __init__(
        self,
        command: list[str],
        *,
        patterns: list[str] | None = None,
        ignore_patterns: list[str] | None = None,
        ignore_directories: bool = False,
        stop_signal: signal.Signals | int = signal.SIGINT,
        kill_after: int = 10,
        debounce_interval_seconds: int = 0,
        restart_on_command_exit: bool = True,
    ):
        if kill_after < 0:
            error = "kill_after must be non-negative."
            raise ValueError(error)
        if debounce_interval_seconds < 0:
            error = "debounce_interval_seconds must be non-negative."
            raise ValueError(error)

        super().__init__(
            patterns=patterns,
            ignore_patterns=ignore_patterns,
            ignore_directories=ignore_directories,
        )

        self.command = command
        self.stop_signal = stop_signal.value if isinstance(stop_signal, signal.Signals) else stop_signal
        self.kill_after = kill_after
        self.debounce_interval_seconds = debounce_interval_seconds
        self.restart_on_command_exit = restart_on_command_exit

        self.process: subprocess.Popen[bytes] | None = None
        self.process_watcher: ProcessWatcher | None = None
        self.event_debouncer: EventDebouncer | None = None
        self.restart_count = 0

        self._is_process_stopping = False
        self._is_trick_stopping = False
        self._stopping_lock = threading.RLock()

    def start(self) -> None:
        if self.debounce_interval_seconds:
            self.event_debouncer = EventDebouncer(
                debounce_interval_seconds=self.debounce_interval_seconds,
                events_callback=lambda events: self._restart_process(),
            )
            self.event_debouncer.start()
        self._start_process()

    def stop(self) -> None:
        # Ensure the body of the function is only run once.
        with self._stopping_lock:
            if self._is_trick_stopping:
                return
            self._is_trick_stopping = True

        process_watcher = self.process_watcher
        if self.event_debouncer is not None:
            self.event_debouncer.stop()
        self._stop_process()

        # Don't leak threads: Wait for background threads to stop.
        if self.event_debouncer is not None:
            self.event_debouncer.join()
        if process_watcher is not None:
            process_watcher.join()

    def _start_process(self) -> None:
        if self._is_trick_stopping:
            return

        # windows doesn't have setsid
        self.process = subprocess.Popen(self.command, preexec_fn=getattr(os, "setsid", None))
        if self.restart_on_command_exit:
            self.process_watcher = ProcessWatcher(self.process, self._restart_process)
            self.process_watcher.start()

    def _stop_process(self) -> None:
        # Ensure the body of the function is not run in parallel in different threads.
        with self._stopping_lock:
            if self._is_process_stopping:
                return
            self._is_process_stopping = True

        try:
            if self.process_watcher is not None:
                self.process_watcher.stop()
                self.process_watcher = None

            if self.process is not None:
                try:
                    kill_process(self.process.pid, self.stop_signal)
                except OSError:
                    # Process is already gone
                    pass
                else:
                    kill_time = time.time() + self.kill_after
                    while time.time() < kill_time:
                        if self.process.poll() is not None:
                            break
                        time.sleep(0.25)
                    else:
                        # Process is already gone
                        with contextlib.suppress(OSError):
                            kill_process(self.process.pid, 9)
                self.process = None
        finally:
            self._is_process_stopping = False

    @echo_events
    def on_any_event(self, event: FileSystemEvent) -> None:
        if event.event_type in {EVENT_TYPE_OPENED, EVENT_TYPE_CLOSED_NO_WRITE}:
            # FIXME: see issue #949, and find a way to better handle that scenario
            return

        if self.event_debouncer is not None:
            self.event_debouncer.handle_event(event)
        else:
            self._restart_process()

    def _restart_process(self) -> None:
        if self._is_trick_stopping:
            return
        self._stop_process()
        self._start_process()
        self.restart_count += 1


if platform.is_windows():

    def kill_process(pid: int, stop_signal: int) -> None:
        os.kill(pid, stop_signal)

else:

    def kill_process(pid: int, stop_signal: int) -> None:
        os.killpg(os.getpgid(pid), stop_signal)
