import functools
import logging
import typing
from http import HTTPStatus

from odoo.netsvc import (
    BOLD_SEQ,
    COLOR_PATTERN,
    CYAN,
    DEFAULT,
    GREEN,
    MAGENTA,
    RED,
    RESET_SEQ,
    YELLOW,
    ColoredFormatter,
)

from .requestlib import DEFAULT_MAX_CONTENT_LENGTH, MAX_FORM_SIZE

_HTTP_EXTRA = {
    'remote_addr': '-',
    'http_request_line': '"- - -"',
    'http_response_status': '-',
    'http_response_body': '-',
    'query_count': '-',
    'query_time': '-',
    'remaining_time': '-',
    'cursor_mode': '-',
}
_HTTP_FORMAT = '%(' + ')s %('.join(_HTTP_EXTRA) + ')s'


def _colorize_request_line(request_line: str, status: int) -> str:
    if status == 200:
        return request_line
    status = HTTPStatus(status)
    if status.is_informational or status.is_success:
        return f'{BOLD_SEQ}{request_line}{RESET_SEQ}'
    if status == HTTPStatus.NOT_MODIFIED:
        return COLOR_PATTERN % (30 + CYAN, 40 + DEFAULT, request_line)
    if status.is_redirection:
        return COLOR_PATTERN % (30 + GREEN, 40 + DEFAULT, request_line)
    if status == HTTPStatus.NOT_FOUND:
        return COLOR_PATTERN % (30 + YELLOW, 40 + DEFAULT, request_line)
    if status.is_client_error:
        return BOLD_SEQ + COLOR_PATTERN % (30 + RED, 40 + DEFAULT, request_line)
    return BOLD_SEQ + COLOR_PATTERN % (30 + MAGENTA, 40 + DEFAULT, request_line)


def _colorize_range(value: float, format: str, low: float, high: float):
    if value > high:
        return COLOR_PATTERN % (30 + RED, 40 + DEFAULT, format % value)
    if value > low:
        return COLOR_PATTERN % (30 + YELLOW, 40 + DEFAULT, format % value)
    return format % value


_colorize_query_count = functools.partial(_colorize_range, format='%d', low=100, high=1000)
_colorize_query_time = functools.partial(_colorize_range, format='%.3f', low=.1, high=3)
_colorize_remaining_time = functools.partial(_colorize_range, format='%.3f', low=1, high=5)


def _colorize_body_length(body_length):
    if body_length == '-':
        return body_length
    if body_length == 'stream':
        return COLOR_PATTERN % (30 + YELLOW, 40 + DEFAULT, body_length)
    return _colorize_range(int(body_length), '%s', low=MAX_FORM_SIZE, high=DEFAULT_MAX_CONTENT_LENGTH)


def _colorize_cursor_mode(cursor_mode: typing.Literal['ro', 'rw', 'ro->rw']) -> str:
    cursor_mode_color = (
             RED    if cursor_mode == 'ro->rw'  # noqa: E272
        else YELLOW if cursor_mode == 'rw'
        else GREEN
    )
    return COLOR_PATTERN % (30 + cursor_mode_color, 40 + DEFAULT, cursor_mode)


@functools.lru_cache(1)
def _has_color():
    return any(
        isinstance(handler.formatter, ColoredFormatter)
        for handler
        in logging.root.handlers
    )


def http_log(logger, level, msg, *args, **kwargs):
    extra = kwargs['extra'] = _HTTP_EXTRA | kwargs.get('extra', {})
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
    else:
        extra['query_time'] = round(extra['query_time'], 3)
        extra['remaining_time'] = round(extra['remaining_time'], 3)
    msg += _HTTP_FORMAT % extra
    logger.log(level, msg, *args, **kwargs)
