""":module: watchdog.watchmedo
:author: yesudeep@google.com (Yesudeep Mangalapilly)
:author: contact@tiger-222.fr (Mickaël Schoentgen)
:synopsis: ``watchmedo`` shell script utility.
"""

from __future__ import annotations

import errno
import logging
import os
import os.path
import sys
import time
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from io import StringIO
from textwrap import dedent
from typing import TYPE_CHECKING, Any

from watchdog.utils import WatchdogShutdownError, load_class, platform
from watchdog.version import VERSION_STRING

if TYPE_CHECKING:
    from argparse import Namespace, _SubParsersAction
    from typing import Callable

    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import ObserverType
    from watchdog.observers.api import BaseObserver


logging.basicConfig(level=logging.INFO)

CONFIG_KEY_TRICKS = "tricks"
CONFIG_KEY_PYTHON_PATH = "python-path"


class HelpFormatter(RawDescriptionHelpFormatter):
    """A nicer help formatter.

    Help for arguments can be indented and contain new lines.
    It will be de-dented and arguments in the help
    will be separated by a blank line for better readability.

    Source: https://github.com/httpie/httpie/blob/2423f89/httpie/cli/argparser.py#L31
    """

    def __init__(self, *args: Any, max_help_position: int = 6, **kwargs: Any) -> None:
        # A smaller indent for args help.
        kwargs["max_help_position"] = max_help_position
        super().__init__(*args, **kwargs)

    def __repr__(self) -> str:
        return f"<{type(self).__name__}>"

    def _split_lines(self, text: str, width: int) -> list[str]:
        text = dedent(text).strip() + "\n\n"
        return text.splitlines()


epilog = """\
Copyright 2018-2024 Mickaël Schoentgen & contributors
Copyright 2014-2018 Thomas Amland & contributors
Copyright 2012-2014 Google, Inc.
Copyright 2011-2012 Yesudeep Mangalapilly

Licensed under the terms of the Apache license, version 2.0. Please see
LICENSE in the source code for more information."""

cli = ArgumentParser(epilog=epilog, formatter_class=HelpFormatter)
cli.add_argument("--version", action="version", version=VERSION_STRING)
subparsers = cli.add_subparsers(dest="top_command")
command_parsers = {}

Argument = tuple[list[str], Any]


def argument(*name_or_flags: str, **kwargs: Any) -> Argument:
    """Convenience function to properly format arguments to pass to the
    command decorator.
    """
    return list(name_or_flags), kwargs


def command(
    args: list[Argument],
    *,
    parent: _SubParsersAction[ArgumentParser] = subparsers,
    cmd_aliases: list[str] | None = None,
) -> Callable:
    """Decorator to define a new command in a sanity-preserving way.
    The function will be stored in the ``func`` variable when the parser
    parses arguments so that it can be called directly like so::

      >>> args = cli.parse_args()
      >>> args.func(args)

    """

    def decorator(func: Callable) -> Callable:
        name = func.__name__.replace("_", "-")
        desc = dedent(func.__doc__ or "")
        parser = parent.add_parser(name, aliases=cmd_aliases or [], description=desc, formatter_class=HelpFormatter)
        command_parsers[name] = parser
        verbosity_group = parser.add_mutually_exclusive_group()
        verbosity_group.add_argument("-q", "--quiet", dest="verbosity", action="append_const", const=-1)
        verbosity_group.add_argument("-v", "--verbose", dest="verbosity", action="append_const", const=1)
        for name_or_flags, kwargs in args:
            parser.add_argument(*name_or_flags, **kwargs)
            parser.set_defaults(func=func)
        return func

    return decorator


def path_split(pathname_spec: str, *, separator: str = os.pathsep) -> list[str]:
    """Splits a pathname specification separated by an OS-dependent separator.

    :param pathname_spec:
        The pathname specification.
    :param separator:
        (OS Dependent) `:` on Unix and `;` on Windows or user-specified.
    """
    return pathname_spec.split(separator)


def add_to_sys_path(pathnames: list[str], *, index: int = 0) -> None:
    """Adds specified paths at specified index into the sys.path list.

    :param paths:
        A list of paths to add to the sys.path
    :param index:
        (Default 0) The index in the sys.path list where the paths will be
        added.
    """
    for pathname in pathnames[::-1]:
        sys.path.insert(index, pathname)


def load_config(tricks_file_pathname: str) -> dict:
    """Loads the YAML configuration from the specified file.

    :param tricks_file_path:
        The path to the tricks configuration file.
    :returns:
        A dictionary of configuration information.
    """
    import yaml

    with open(tricks_file_pathname, "rb") as f:
        return yaml.safe_load(f.read())


def parse_patterns(
    patterns_spec: str, ignore_patterns_spec: str, *, separator: str = ";"
) -> tuple[list[str], list[str]]:
    """Parses pattern argument specs and returns a two-tuple of
    (patterns, ignore_patterns).
    """
    patterns = patterns_spec.split(separator)
    ignore_patterns = ignore_patterns_spec.split(separator)
    if ignore_patterns == [""]:
        ignore_patterns = []
    return patterns, ignore_patterns


def observe_with(
    observer: BaseObserver,
    event_handler: FileSystemEventHandler,
    pathnames: list[str],
    *,
    recursive: bool,
) -> None:
    """Single observer thread with a scheduled path and event handler.

    :param observer:
        The observer thread.
    :param event_handler:
        Event handler which will be called in response to file system events.
    :param pathnames:
        A list of pathnames to monitor.
    :param recursive:
        ``True`` if recursive; ``False`` otherwise.
    """
    for pathname in set(pathnames):
        observer.schedule(event_handler, pathname, recursive=recursive)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except WatchdogShutdownError:
        observer.stop()
    observer.join()


def schedule_tricks(observer: BaseObserver, tricks: list[dict], pathname: str, *, recursive: bool) -> None:
    """Schedules tricks with the specified observer and for the given watch
    path.

    :param observer:
        The observer thread into which to schedule the trick and watch.
    :param tricks:
        A list of tricks.
    :param pathname:
        A path name which should be watched.
    :param recursive:
        ``True`` if recursive; ``False`` otherwise.
    """
    for trick in tricks:
        for name, value in trick.items():
            trick_cls = load_class(name)
            handler = trick_cls(**value)
            trick_pathname = getattr(handler, "source_directory", None) or pathname
            observer.schedule(handler, trick_pathname, recursive=recursive)


@command(
    [
        argument("files", nargs="*", help="perform tricks from given file"),
        argument(
            "--python-path",
            default=".",
            help=f"Paths separated by {os.pathsep!r} to add to the Python path.",
        ),
        argument(
            "--interval",
            "--timeout",
            dest="timeout",
            default=1.0,
            type=float,
            help="Use this as the polling interval/blocking timeout (in seconds).",
        ),
        argument(
            "--recursive",
            action="store_true",
            default=True,
            help="Recursively monitor paths (defaults to True).",
        ),
        argument("--debug-force-polling", action="store_true", help="[debug] Forces polling."),
        argument(
            "--debug-force-kqueue",
            action="store_true",
            help="[debug] Forces BSD kqueue(2).",
        ),
        argument(
            "--debug-force-winapi",
            action="store_true",
            help="[debug] Forces Windows API.",
        ),
        argument(
            "--debug-force-fsevents",
            action="store_true",
            help="[debug] Forces macOS FSEvents.",
        ),
        argument(
            "--debug-force-inotify",
            action="store_true",
            help="[debug] Forces Linux inotify(7).",
        ),
    ],
    cmd_aliases=["tricks"],
)
def tricks_from(args: Namespace) -> None:
    """Command to execute tricks from a tricks configuration file."""
    observer_cls: ObserverType
    if args.debug_force_polling:
        from watchdog.observers.polling import PollingObserver

        observer_cls = PollingObserver
    elif args.debug_force_kqueue:
        from watchdog.observers.kqueue import KqueueObserver

        observer_cls = KqueueObserver
    elif (not TYPE_CHECKING and args.debug_force_winapi) or (TYPE_CHECKING and platform.is_windows()):
        from watchdog.observers.read_directory_changes import WindowsApiObserver

        observer_cls = WindowsApiObserver
    elif args.debug_force_inotify:
        from watchdog.observers.inotify import InotifyObserver

        observer_cls = InotifyObserver
    elif args.debug_force_fsevents:
        from watchdog.observers.fsevents import FSEventsObserver

        observer_cls = FSEventsObserver
    else:
        # Automatically picks the most appropriate observer for the platform
        # on which it is running.
        from watchdog.observers import Observer

        observer_cls = Observer

    add_to_sys_path(path_split(args.python_path))
    observers = []
    for tricks_file in args.files:
        observer = observer_cls(timeout=args.timeout)

        if not os.path.exists(tricks_file):
            raise OSError(errno.ENOENT, os.strerror(errno.ENOENT), tricks_file)

        config = load_config(tricks_file)

        try:
            tricks = config[CONFIG_KEY_TRICKS]
        except KeyError as e:
            error = f"No {CONFIG_KEY_TRICKS!r} key specified in {tricks_file!r}."
            raise KeyError(error) from e

        if CONFIG_KEY_PYTHON_PATH in config:
            add_to_sys_path(config[CONFIG_KEY_PYTHON_PATH])

        dir_path = os.path.dirname(tricks_file) or os.path.relpath(os.getcwd())
        schedule_tricks(observer, tricks, dir_path, recursive=args.recursive)
        observer.start()
        observers.append(observer)

    try:
        while True:
            time.sleep(1)
    except WatchdogShutdownError:
        for o in observers:
            o.unschedule_all()
            o.stop()
    for o in observers:
        o.join()


@command(
    [
        argument(
            "trick_paths",
            nargs="*",
            help="Dotted paths for all the tricks you want to generate.",
        ),
        argument(
            "--python-path",
            default=".",
            help=f"Paths separated by {os.pathsep!r} to add to the Python path.",
        ),
        argument(
            "--append-to-file",
            default=None,
            help="""
                   Appends the generated tricks YAML to a file.
                   If not specified, prints to standard output.""",
        ),
        argument(
            "-a",
            "--append-only",
            dest="append_only",
            action="store_true",
            help="""
                   If --append-to-file is not specified, produces output for
                   appending instead of a complete tricks YAML file.""",
        ),
    ],
    cmd_aliases=["generate-tricks-yaml"],
)
def tricks_generate_yaml(args: Namespace) -> None:
    """Command to generate Yaml configuration for tricks named on the command line."""
    import yaml

    python_paths = path_split(args.python_path)
    add_to_sys_path(python_paths)
    output = StringIO()

    for trick_path in args.trick_paths:
        trick_cls = load_class(trick_path)
        output.write(trick_cls.generate_yaml())

    content = output.getvalue()
    output.close()

    header = yaml.dump({CONFIG_KEY_PYTHON_PATH: python_paths})
    header += f"{CONFIG_KEY_TRICKS}:\n"
    if args.append_to_file is None:
        # Output to standard output.
        if not args.append_only:
            content = header + content
        sys.stdout.write(content)
    else:
        if not os.path.exists(args.append_to_file):
            content = header + content
        with open(args.append_to_file, "a", encoding="utf-8") as file:
            file.write(content)


@command(
    [
        argument(
            "directories",
            nargs="*",
            default=".",
            help="Directories to watch. (default: '.').",
        ),
        argument(
            "-p",
            "--pattern",
            "--patterns",
            dest="patterns",
            default="*",
            help="Matches event paths with these patterns (separated by ;).",
        ),
        argument(
            "-i",
            "--ignore-pattern",
            "--ignore-patterns",
            dest="ignore_patterns",
            default="",
            help="Ignores event paths with these patterns (separated by ;).",
        ),
        argument(
            "-D",
            "--ignore-directories",
            dest="ignore_directories",
            action="store_true",
            help="Ignores events for directories.",
        ),
        argument(
            "-R",
            "--recursive",
            dest="recursive",
            action="store_true",
            help="Monitors the directories recursively.",
        ),
        argument(
            "--interval",
            "--timeout",
            dest="timeout",
            default=1.0,
            type=float,
            help="Use this as the polling interval/blocking timeout.",
        ),
        argument("--debug-force-polling", action="store_true", help="[debug] Forces polling."),
        argument(
            "--debug-force-kqueue",
            action="store_true",
            help="[debug] Forces BSD kqueue(2).",
        ),
        argument(
            "--debug-force-winapi",
            action="store_true",
            help="[debug] Forces Windows API.",
        ),
        argument(
            "--debug-force-fsevents",
            action="store_true",
            help="[debug] Forces macOS FSEvents.",
        ),
        argument(
            "--debug-force-inotify",
            action="store_true",
            help="[debug] Forces Linux inotify(7).",
        ),
    ],
)
def log(args: Namespace) -> None:
    """Command to log file system events to the console."""
    from watchdog.tricks import LoggerTrick

    patterns, ignore_patterns = parse_patterns(args.patterns, args.ignore_patterns)
    handler = LoggerTrick(
        patterns=patterns,
        ignore_patterns=ignore_patterns,
        ignore_directories=args.ignore_directories,
    )

    observer_cls: ObserverType
    if args.debug_force_polling:
        from watchdog.observers.polling import PollingObserver

        observer_cls = PollingObserver
    elif args.debug_force_kqueue:
        from watchdog.observers.kqueue import KqueueObserver

        observer_cls = KqueueObserver
    elif (not TYPE_CHECKING and args.debug_force_winapi) or (TYPE_CHECKING and platform.is_windows()):
        from watchdog.observers.read_directory_changes import WindowsApiObserver

        observer_cls = WindowsApiObserver
    elif args.debug_force_inotify:
        from watchdog.observers.inotify import InotifyObserver

        observer_cls = InotifyObserver
    elif args.debug_force_fsevents:
        from watchdog.observers.fsevents import FSEventsObserver

        observer_cls = FSEventsObserver
    else:
        # Automatically picks the most appropriate observer for the platform
        # on which it is running.
        from watchdog.observers import Observer

        observer_cls = Observer

    observer = observer_cls(timeout=args.timeout)
    observe_with(observer, handler, args.directories, recursive=args.recursive)


@command(
    [
        argument("directories", nargs="*", default=".", help="Directories to watch."),
        argument(
            "-c",
            "--command",
            dest="command",
            default=None,
            help="""
    Shell command executed in response to matching events.
    These interpolation variables are available to your command string:

        ${watch_src_path}   - event source path
        ${watch_dest_path}  - event destination path (for moved events)
        ${watch_event_type} - event type
        ${watch_object}     - 'file' or 'directory'

    Note:
        Please ensure you do not use double quotes (") to quote
        your command string. That will force your shell to
        interpolate before the command is processed by this
        command.

    Example:

        --command='echo "${watch_src_path}"'
    """,
        ),
        argument(
            "-p",
            "--pattern",
            "--patterns",
            dest="patterns",
            default="*",
            help="Matches event paths with these patterns (separated by ;).",
        ),
        argument(
            "-i",
            "--ignore-pattern",
            "--ignore-patterns",
            dest="ignore_patterns",
            default="",
            help="Ignores event paths with these patterns (separated by ;).",
        ),
        argument(
            "-D",
            "--ignore-directories",
            dest="ignore_directories",
            default=False,
            action="store_true",
            help="Ignores events for directories.",
        ),
        argument(
            "-R",
            "--recursive",
            dest="recursive",
            action="store_true",
            help="Monitors the directories recursively.",
        ),
        argument(
            "--interval",
            "--timeout",
            dest="timeout",
            default=1.0,
            type=float,
            help="Use this as the polling interval/blocking timeout.",
        ),
        argument(
            "-w",
            "--wait",
            dest="wait_for_process",
            action="store_true",
            help="Wait for process to finish to avoid multiple simultaneous instances.",
        ),
        argument(
            "-W",
            "--drop",
            dest="drop_during_process",
            action="store_true",
            help="Ignore events that occur while command is still being"
            " executed to avoid multiple simultaneous instances.",
        ),
        argument("--debug-force-polling", action="store_true", help="[debug] Forces polling."),
    ],
)
def shell_command(args: Namespace) -> None:
    """Command to execute shell commands in response to file system events."""
    from watchdog.tricks import ShellCommandTrick

    if not args.command:
        args.command = None

    observer_cls: ObserverType
    if args.debug_force_polling:
        from watchdog.observers.polling import PollingObserver

        observer_cls = PollingObserver
    else:
        from watchdog.observers import Observer

        observer_cls = Observer

    patterns, ignore_patterns = parse_patterns(args.patterns, args.ignore_patterns)
    handler = ShellCommandTrick(
        args.command,
        patterns=patterns,
        ignore_patterns=ignore_patterns,
        ignore_directories=args.ignore_directories,
        wait_for_process=args.wait_for_process,
        drop_during_process=args.drop_during_process,
    )
    observer = observer_cls(timeout=args.timeout)
    observe_with(observer, handler, args.directories, recursive=args.recursive)


@command(
    [
        argument("command", help="Long-running command to run in a subprocess."),
        argument(
            "command_args",
            metavar="arg",
            nargs="*",
            help="""
    Command arguments.

    Note: Use -- before the command arguments, otherwise watchmedo will
    try to interpret them.
    """,
        ),
        argument(
            "-d",
            "--directory",
            dest="directories",
            metavar="DIRECTORY",
            action="append",
            help="Directory to watch. Use another -d or --directory option for each directory.",
        ),
        argument(
            "-p",
            "--pattern",
            "--patterns",
            dest="patterns",
            default="*",
            help="Matches event paths with these patterns (separated by ;).",
        ),
        argument(
            "-i",
            "--ignore-pattern",
            "--ignore-patterns",
            dest="ignore_patterns",
            default="",
            help="Ignores event paths with these patterns (separated by ;).",
        ),
        argument(
            "-D",
            "--ignore-directories",
            dest="ignore_directories",
            default=False,
            action="store_true",
            help="Ignores events for directories.",
        ),
        argument(
            "-R",
            "--recursive",
            dest="recursive",
            action="store_true",
            help="Monitors the directories recursively.",
        ),
        argument(
            "--interval",
            "--timeout",
            dest="timeout",
            default=1.0,
            type=float,
            help="Use this as the polling interval/blocking timeout.",
        ),
        argument(
            "--signal",
            dest="signal",
            default="SIGINT",
            help="Stop the subprocess with this signal (default SIGINT).",
        ),
        argument("--debug-force-polling", action="store_true", help="[debug] Forces polling."),
        argument(
            "--kill-after",
            dest="kill_after",
            default=10.0,
            type=float,
            help="When stopping, kill the subprocess after the specified timeout in seconds (default 10.0).",
        ),
        argument(
            "--debounce-interval",
            dest="debounce_interval",
            default=0.0,
            type=float,
            help="After a file change, Wait until the specified interval (in "
            "seconds) passes with no file changes, and only then restart.",
        ),
        argument(
            "--no-restart-on-command-exit",
            dest="restart_on_command_exit",
            default=True,
            action="store_false",
            help="Don't auto-restart the command after it exits.",
        ),
    ],
)
def auto_restart(args: Namespace) -> None:
    """Command to start a long-running subprocess and restart it on matched events."""
    observer_cls: ObserverType
    if args.debug_force_polling:
        from watchdog.observers.polling import PollingObserver

        observer_cls = PollingObserver
    else:
        from watchdog.observers import Observer

        observer_cls = Observer

    import signal

    from watchdog.tricks import AutoRestartTrick

    if not args.directories:
        args.directories = ["."]

    # Allow either signal name or number.
    stop_signal = getattr(signal, args.signal) if args.signal.startswith("SIG") else int(args.signal)

    # Handle termination signals by raising a semantic exception which will
    # allow us to gracefully unwind and stop the observer
    termination_signals = {signal.SIGTERM, signal.SIGINT}

    if hasattr(signal, "SIGHUP"):
        termination_signals.add(signal.SIGHUP)

    def handler_termination_signal(_signum: signal._SIGNUM, _frame: object) -> None:
        # Neuter all signals so that we don't attempt a double shutdown
        for signum in termination_signals:
            signal.signal(signum, signal.SIG_IGN)
        raise WatchdogShutdownError

    for signum in termination_signals:
        signal.signal(signum, handler_termination_signal)

    patterns, ignore_patterns = parse_patterns(args.patterns, args.ignore_patterns)
    command = [args.command]
    command.extend(args.command_args)
    handler = AutoRestartTrick(
        command,
        patterns=patterns,
        ignore_patterns=ignore_patterns,
        ignore_directories=args.ignore_directories,
        stop_signal=stop_signal,
        kill_after=args.kill_after,
        debounce_interval_seconds=args.debounce_interval,
        restart_on_command_exit=args.restart_on_command_exit,
    )
    handler.start()
    observer = observer_cls(timeout=args.timeout)
    try:
        observe_with(observer, handler, args.directories, recursive=args.recursive)
    except WatchdogShutdownError:
        pass
    finally:
        handler.stop()


class LogLevelError(Exception):
    pass


def _get_log_level_from_args(args: Namespace) -> str:
    verbosity = sum(args.verbosity or [])
    if verbosity < -1:
        error = "-q/--quiet may be specified only once."
        raise LogLevelError(error)
    if verbosity > 2:
        error = "-v/--verbose may be specified up to 2 times."
        raise LogLevelError(error)
    return ["ERROR", "WARNING", "INFO", "DEBUG"][1 + verbosity]


def main() -> int:
    """Entry-point function."""
    args = cli.parse_args()
    if args.top_command is None:
        cli.print_help()
        return 1

    try:
        log_level = _get_log_level_from_args(args)
    except LogLevelError as exc:
        print(f"Error: {exc.args[0]}", file=sys.stderr)  # noqa:T201
        command_parsers[args.top_command].print_help()
        return 1
    logging.getLogger("watchdog").setLevel(log_level)

    try:
        args.func(args)
    except KeyboardInterrupt:
        return 130

    return 0


if __name__ == "__main__":
    sys.exit(main())
