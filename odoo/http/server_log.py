import functools
import logging
import pprint
import threading
import time
import typing
from http import HTTPStatus
from wsgiref.handlers import format_date_time

import h11

from odoo.netsvc import (
    BOLD_SEQ,
    COLOR_PATTERN,
    CYAN,
    DEFAULT,
    GREEN,
    MAGENTA,
    PID_COLORS,
    RED,
    RESET_SEQ,
    TRUE_COLOR_PATTERN,
    YELLOW,
    ColoredFormatter,
)
from odoo.tools import frozendict
from odoo.tools.misc import real_time

from .requestlib import DEFAULT_MAX_CONTENT_LENGTH, MAX_FORM_SIZE

__all__ = (
    'http_log',
    'reset_thread_info',
)

_HTTP_FORMAT = '%(remote_addr)s %(ident)s %(http_auth)s [%(date)s] "%(http_request_line)s" %(http_response_status)s %(http_response_body)s %(query_count)s %(query_time)s %(remaining_time)s %(cursor_mode)s'
_HTTP_FORMAT_HEADERS = _HTTP_FORMAT + "\n%(http_headers)s"

# All the fallback values for _HTTP_FORMAT(_HEADERS)?
_HTTP_EXTRA = frozendict({
    'remote_addr': '-',
    'ident': '-',  # shortened session id
    'http_auth': '-',  # unused
    'date': '30/Feb/1970 00:00:00',
    'http_request_line': '- - HTTP/?',  # method path version
    'http_response_status': '-',
    'http_response_body': '-',
    'query_count': 0,
    'query_time': 0.0,
    'remaining_time': 0.0,  # total time - query time
    'cursor_mode': '-',
    'http_headers': (),
})

# The responses that never have a body and need no Content-Length header.
_NO_BODY_STATUS = {
    HTTPStatus.CONTINUE,
    HTTPStatus.SWITCHING_PROTOCOLS,
    HTTPStatus.PROCESSING,
    HTTPStatus.EARLY_HINTS,
    HTTPStatus.NO_CONTENT,
    HTTPStatus.RESET_CONTENT,
    HTTPStatus.NOT_MODIFIED,
}


def reset_thread_info():
    t0 = real_time()
    current_thread = threading.current_thread()
    current_thread.query_count = 0
    current_thread.query_time = 0
    current_thread.perf_t0 = t0
    current_thread.cursor_mode = None
    current_thread.rpc_model_method = None
    current_thread.sess_id = None


def http_log(
    level,
    msg,
    *args,
    req: h11.Request | None,
    res: h11.Response | None,
    **kwargs,
):
    if not _logger.isEnabledFor(level):
        return

    now = time.time()
    real_now = real_time()
    current_thread = threading.current_thread()
    extra = dict(
        _HTTP_EXTRA,
        query_count=current_thread.query_count,
        query_time=current_thread.query_time,
        remaining_time=real_now - current_thread.perf_t0 - current_thread.query_time,
        date=format_date_time(now),
    )
    if th_cursor_mode := current_thread.cursor_mode:
        extra['cursor_mode'] = th_cursor_mode
    if th_sess_id := current_thread.sess_id:
        extra['ident'] = th_sess_id

    if req:
        extra['http_headers'] = req.headers
        extra['http_request_line'] = ((
            b'%(method)s %(target)s#%(rpc)s HTTP/%(version)s'
            if (rmm := current_thread.rpc_model_method) else
            b'%(method)s %(target)s HTTP/%(version)s'
        ) % {
            b'method': req.method if req else b'-',
            b'target': req.target if req else b'-',
            b'rpc': rmm and rmm.encode(),
            b'version': req.http_version if req else b'-',
        }).decode()

    if res:
        extra['http_response_status'] = res.status_code
        extra['http_headers'] = res.headers
        res_content_length = next(
            (v for k, v in res.headers if k == b'content-length'), None)
        extra['http_response_body'] = (
            int(res_content_length) if res_content_length is not None
            else 0 if res.status_code in _NO_BODY_STATUS
            else 'stream'
        )
        # "Thu, 30 Apr 2026 16:18:06 GMT" => "30/Apr/2026 16:18:06"
        res_http_date = next(v for k, v in res.headers if k == b'date').decode()
        extra['date'] = res_http_date[5:-4].replace(' ', '/', 2)

    extra.update(kwargs.get('extra', {}))
    kwargs['extra'] = extra.copy()  # before we set colors

    if _has_color():
        extra['query_count'] = _colorize_query_count(extra['query_count'])
        extra['query_time'] = _colorize_query_time(extra['query_time'])
        extra['remaining_time'] = _colorize_remaining_time(extra['remaining_time'])
        if extra['http_response_status'] != '-':
            extra['http_request_line'] = _colorize_request_line(
                extra['http_request_line'], extra['http_response_status'])
        if extra['cursor_mode'] != '-':
            extra['cursor_mode'] = _colorize_cursor_mode(extra['cursor_mode'])
        extra['http_response_body'] = _colorize_body_length(extra['http_response_body'])
        extra['ident'] = _colorize_ident(extra['ident'])
    else:
        extra['query_time'] = round(extra['query_time'], 3)
        extra['remaining_time'] = round(extra['remaining_time'], 3)

    if extra['http_headers'] and _logger_headers.isEnabledFor(logging.DEBUG):
        extra['http_headers'] = pprint.pformat(list(extra['http_headers']))

    msg += (
        _HTTP_FORMAT_HEADERS
        if extra['http_headers'] and _logger_headers.isEnabledFor(logging.DEBUG) else
        _HTTP_FORMAT
    ) % extra

    _logger.log(level, msg, *args, **kwargs)


def _colorize_ident(ident: str) -> str:
    if ident == '-':
        return '-'
    return TRUE_COLOR_PATTERN % (PID_COLORS[int.from_bytes(ident.encode()) % len(PID_COLORS)], ident)


def _colorize_request_line(request_line: str, status: int) -> str:
    """
    Return ``request_line`` as a colored string depending on ``status``.
    """
    if status == 200:
        return request_line
    status = HTTPStatus(status)
    if status == HTTPStatus.NOT_MODIFIED:
        return COLOR_PATTERN % (30 + CYAN, 40 + DEFAULT, request_line)
    if status == HTTPStatus.NOT_FOUND:
        return COLOR_PATTERN % (30 + YELLOW, 40 + DEFAULT, request_line)
    if status.is_informational or status.is_success:
        return f'{BOLD_SEQ}{request_line}{RESET_SEQ}'
    if status.is_redirection:
        return COLOR_PATTERN % (30 + GREEN, 40 + DEFAULT, request_line)
    if status.is_client_error:
        return BOLD_SEQ + COLOR_PATTERN % (30 + RED, 40 + DEFAULT, request_line)
    # status.is_server_error, and bad status codes
    return BOLD_SEQ + COLOR_PATTERN % (30 + MAGENTA, 40 + DEFAULT, request_line)


def _colorize_range(value: float, format: str, low: float, high: float) -> str:
    """
    Return ``value`` as a colored string:

    * ``high < value``: red
    * ``low < value < high``: yellow
    * ``value < low``: no color
    """
    if value > high:
        return COLOR_PATTERN % (30 + RED, 40 + DEFAULT, format % value)
    if value > low:
        return COLOR_PATTERN % (30 + YELLOW, 40 + DEFAULT, format % value)
    return format % value


_colorize_query_count = functools.partial(_colorize_range, format='%d', low=100, high=1000)
_colorize_query_time = functools.partial(_colorize_range, format='%.3f', low=.1, high=3)
_colorize_remaining_time = functools.partial(_colorize_range, format='%.3f', low=1, high=5)


def _colorize_body_length(body_length: int | typing.Literal['-', 'stream']) -> str:
    """
    Return ``body_length`` as a colored string.

    It is colored in red when the length is higher than the maximum body
    length we accept (128 MiB). It is colored in yellow when we don't
    know the length (stream) or when the length is higher than the
    largest form we accept (10 MiB). Otherwise the length is returned
    with no color.
    """
    if body_length == '-':
        return body_length
    if body_length == 'stream':
        return COLOR_PATTERN % (30 + YELLOW, 40 + DEFAULT, body_length)
    return _colorize_range(int(body_length), '%s', low=MAX_FORM_SIZE, high=DEFAULT_MAX_CONTENT_LENGTH)


def _colorize_cursor_mode(cursor_mode: typing.Literal['ro', 'rw', 'ro->rw']) -> str:
    """
    Return ``cursor_mode`` as a colored string.

    * Requests read-only: green.
    * Requests read/write: yellow.
    * Requests that were attempted with a read-only cursor, but failed
      and had to be repeated using a read/write one: red.
    """
    cursor_mode_color = (
             RED    if cursor_mode == 'ro->rw'  # noqa: E272
        else YELLOW if cursor_mode == 'rw'
        else GREEN
    )
    return COLOR_PATTERN % (30 + cursor_mode_color, 40 + DEFAULT, cursor_mode)


@functools.cache
def _has_color():
    """ Determine if the root logger supports colors. """
    return any(
        isinstance(handler.formatter, ColoredFormatter)
        for handler
        in logging.root.handlers
    )


_logger = logging.getLogger('odoo.http.server')
_logger_headers = _logger.getChild('headers')
_logger_headers.setLevel(logging.WARNING)  # disabled by default
