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

    DEFAULT_IMPLICIT_RECORD_KEYS = {
        'message',  # prefered to msg and args to have the corrsct args formating
        'test',  # needed on runbot
        'exc_info',  # needed on runbot, concataneted to message implicilty in some cases
    }

    DEFAULT_IGNORED_RECORD_KEYS = {
                'msecs',  # derived from created
                'relativeCreated',  # derived from created
                'asctime',  # derived from created
                'filename',  # derived from pathname
                'module',  # derived from filename (pathname)
                'msg',  # formatted in message
                'args',  # formatted in message
    }

    def __init__(self, *args, record_keys=None, ignore_record_keys=None, additional_record_keys=None, **kwargs):
        """
        :param record_keys: list of keys to include in the json output, if None, all keys are included except those in ignore_record_keys
        :param ignore_record_keys: list of keys to ignore in the json output, if None, a default list of keys is used. Only used if record_keys is None
        :param additional_record_keys: list of additional keys to include in the json output
        """
        super().__init__(*args, **kwargs)
        if record_keys is not None and (ignore_record_keys is not None or additional_record_keys is not None):
            raise ValueError("record_keys is exclusive with ignore_record_keys / additional_record_keys")
        self.record_keys = record_keys
        self.additional_record_keys = set(additional_record_keys) if additional_record_keys else set()
        self.ignore_record_keys = set(ignore_record_keys) if ignore_record_keys else set()

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
        record_keys = (record.__dict__.keys() | self.DEFAULT_IMPLICIT_RECORD_KEYS) - self.DEFAULT_IGNORED_RECORD_KEYS
        return sorted((record_keys - self.ignore_record_keys) | self.additional_record_keys)
