#!/usr/bin/env python3

EX_USAGE = 64
EX_NOUSER = 67
EX_NOHOST = 68
EX_UNAVAILABLE = 69
EX_SOFTWARE = 70
EX_TEMPFAIL = 75
EX_NOPERM = 77
EX_CONFIG = 78

FAULT_APPLICATION_ERROR = 1
FAULT_ACCESS_DENIED = 3

RETRYABLE_HTTP_STATUSES = frozenset({429, 500, 502, 503, 504})

DEFAULT_TIMEOUT = 60


import sys  # noqa: E402 - sys must exist before the guarded import block below, whose handler writes to stderr

try:
    import argparse
    import pathlib
    import socket
    import traceback
    import xmlrpc.client as xmlrpclib
    from typing import NoReturn
except ImportError as e:
    sys.stderr.write("%s\n" % e)
    sys.exit(EX_SOFTWARE)


class ArgumentParser(argparse.ArgumentParser):
    def exit(self, status: int = 0, message: str | None = None) -> NoReturn:
        if message:
            sys.stderr.write(message)
        sys.exit(0 if status == 0 else EX_USAGE)


def postfix_exit(
    exit_code: int = EX_SOFTWARE, message: str | None = None, debug: bool = False
) -> NoReturn:
    try:
        if debug:
            traceback.print_exc(None, sys.stderr)
        if message:
            sys.stderr.write(message)
    except Exception:  # noqa: S110 - already on the failure path; a failure to report it must not mask the original
        pass
    finally:
        sys.exit(exit_code)


def prepare_mailgate_parser() -> ArgumentParser:
    parser = ArgumentParser(
        prog="odoo-mailgate.py", description="Pipe an incoming email into Odoo."
    )
    parser.add_argument("--version", action="version", version="%(prog)s v2.0")
    parser.add_argument(
        "-d",
        "--database",
        default="odoo",
        help="Odoo database name (default: %(default)s)",
    )
    parser.add_argument(
        "-u",
        "--userid",
        type=int,
        default=1,
        help="Odoo user id to connect with (default: %(default)s)",
    )
    parser.add_argument(
        "-p",
        "--password",
        default="admin",
        help="Odoo user password (default: %(default)s)",
    )
    parser.add_argument(
        "--password-file",
        help="Read the password from this file instead of the command line, "
        "where every local user can read it out of the process table",
    )
    parser.add_argument(
        "--host", default="localhost", help="Odoo host (default: %(default)s)"
    )
    parser.add_argument(
        "--port", type=int, default=8069, help="Odoo port (default: %(default)s)"
    )
    parser.add_argument(
        "--proto",
        dest="protocol",
        choices=("http", "https"),
        default="http",
        help="Protocol to use (default: %(default)s)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT,
        help="Seconds to wait for Odoo before giving up (default: %(default)s). "
        "Without one a stalled server holds this delivery slot indefinitely",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug (may lead to stack traces in bounce mails)",
    )
    parser.add_argument(
        "--retry-status",
        dest="retry",
        action="store_true",
        help="Send temporary failure status code on connection errors.",
    )
    return parser


def read_password(options: argparse.Namespace) -> str:
    if not options.password_file:
        return options.password
    try:
        return (
            pathlib.Path(options.password_file).read_text(encoding="utf-8").strip("\n")
        )
    except OSError as err:
        postfix_exit(EX_CONFIG, "cannot read password file: %s\n" % err, options.debug)


def handle_fault(err: xmlrpclib.Fault, options: argparse.Namespace) -> NoReturn:
    if err.faultCode == FAULT_ACCESS_DENIED:
        postfix_exit(EX_NOPERM, debug=False)
    if err.faultCode != FAULT_APPLICATION_ERROR:
        postfix_exit(EX_SOFTWARE, "xmlrpclib.Fault\n", options.debug)
    if "database" in err.faultString and "does not exist" in err.faultString:
        postfix_exit(
            EX_CONFIG, "database does not exist: %s\n" % options.database, options.debug
        )
    if "No possible route" in err.faultString:
        postfix_exit(EX_NOUSER, "alias does not exist in odoo\n", options.debug)
    postfix_exit(EX_SOFTWARE, "xmlrpclib.Fault\n", options.debug)


def main() -> None:
    options = prepare_mailgate_parser().parse_args()
    password = read_password(options)

    msg = sys.stdin.buffer.read()

    socket.setdefaulttimeout(options.timeout)

    try:
        models = xmlrpclib.ServerProxy(
            "%s://%s:%s/xmlrpc/2/object"
            % (options.protocol, options.host, options.port),
            allow_none=True,
        )
        models.execute_kw(
            options.database,
            options.userid,
            password,
            "mixin.mail.thread",
            "message_process",
            [False, xmlrpclib.Binary(msg)],
            {},
        )
    except xmlrpclib.Fault as err:
        handle_fault(err, options)
    except xmlrpclib.ProtocolError as err:
        retryable = err.errcode in RETRYABLE_HTTP_STATUSES
        postfix_exit(
            exit_code=EX_TEMPFAIL if (retryable and options.retry) else EX_UNAVAILABLE,
            message="http error: %s %s (%s)\n"
            % (err.errcode, err.errmsg, options.host),
            debug=options.debug,
        )
    except OSError as err:
        postfix_exit(
            exit_code=EX_TEMPFAIL if options.retry else EX_NOHOST,
            message="connection error: %s: %s (%s)\n"
            % (err.__class__.__name__, err, options.host),
            debug=options.debug,
        )
    except Exception:
        postfix_exit(EX_SOFTWARE, "", options.debug)


try:
    if __name__ == "__main__":
        main()
except Exception:
    postfix_exit(EX_SOFTWARE, "", True)
