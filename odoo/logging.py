import contextlib
import json
import logging

from odoo.netsvc import ColoredFormatter, PostgreSQLHandler

__all__ = [  # noqa: RUF022
    "ColoredFormatter",
    "JSONFormatter",
    "PostgreSQLHandler",
]


class JSONFormatter(logging.Formatter):
    def __init__(self, *args, record_keys=None, ignore_record_keys=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.record_keys = record_keys
        if ignore_record_keys is not None:
            self.ignore_record_keys = set(ignore_record_keys)
        else:
            # by default we want only the lower level key, avoiding to have duplicated information.
            # message is derived from msg and args, but once formatted to json and the args stringified,
            # it is not possible to format the message, so we keep the message instead
            self.ignore_record_keys = {
                'msecs',  # derived from created
                'relativeCreated',  # derived from created
                'asctime',  # derived from created
                'filename',  # derived from pathname
                'module',  # derived from filename (pathname)
                'msg',  # formatted in message
                'args',  # formatted in message
            }

    def format(self, record):
        record_json = {}
        record_keys = self.record_keys
        if record_keys is None:
            record_keys = self._get_default_record_keys(record)
        for key in record_keys:
            if key == 'exc_info':
                if record.exc_info:
                    if not record.exc_text:
                        record.exc_text = self.formatException(record.exc_info)
                    record_json[key] = record.exc_text
            elif key == 'stack_info':  # this case is not 100% necessary but allows to override the default stack_info formatting
                if record.stack_info:
                    record_json[key] = self.formatStack(record.stack_info)
            elif key == 'message':
                record.message = record.getMessage()
                record_json[key] = record.message
            elif key == 'asctime':
                record.asctime = self.formatTime(record, self.datefmt)
                record_json[key] = record.asctime
            elif key == 'test':
                from .modules import module  # noqa: PLC0415
                if module.current_test:
                    with contextlib.suppress(Exception):
                        record_json[key] = module.current_test.get_log_metadata()
            else:
                value = getattr(record, key, None)
                if value is not None:
                    record_json[key] = value

        return json.dumps(record_json, default=str)

    def _get_default_record_keys(self, record):
        return list(record.__dict__.keys() | {'message'} - self.ignore_record_keys)
