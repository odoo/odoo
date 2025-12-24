# -*- coding: utf-8 -*-
import logging
import json
from datetime import datetime

# Try to import optional dependencies
try:
    import structlog
    STRUCTLOG_AVAILABLE = True
except ImportError:
    STRUCTLOG_AVAILABLE = False

# Handle pythonjsonlogger - try new location first, then old
JSONLOGGER_AVAILABLE = False
JsonFormatter = None
try:
    from pythonjsonlogger.json import JsonFormatter
    JSONLOGGER_AVAILABLE = True
except ImportError:
    try:
        from pythonjsonlogger.jsonlogger import JsonFormatter
        JSONLOGGER_AVAILABLE = True
    except ImportError:
        pass


class SimpleJSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
        }
        if hasattr(record, 'event'):
            log_data['event'] = record.event
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'created', 'filename', 'funcName',
                           'levelname', 'levelno', 'lineno', 'module', 'msecs',
                           'message', 'pathname', 'process', 'processName',
                           'relativeCreated', 'thread', 'threadName', 'exc_info',
                           'exc_text', 'stack_info']:
                log_data[key] = value
        return json.dumps(log_data)


class ViaSuiteLoggerAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        extra = kwargs.get('extra', {})
        if isinstance(msg, str) and extra:
            extra['event'] = msg
            kwargs['extra'] = extra
        return msg, kwargs


class ViaSuiteLogger:
    _configured = False

    @classmethod
    def configure(cls, log_level='INFO'):
        if cls._configured:
            return

        log_level_int = getattr(logging, log_level.upper(), logging.INFO)
        log_handler = logging.StreamHandler()

        if JSONLOGGER_AVAILABLE:
            formatter = JsonFormatter(
                '%(timestamp)s %(level)s %(name)s %(message)s',
                rename_fields={'name': 'logger', 'levelname': 'level'},
                timestamp=True
            )
        else:
            formatter = SimpleJSONFormatter()

        log_handler.setFormatter(formatter)
        root_logger = logging.getLogger()
        root_logger.addHandler(log_handler)
        root_logger.setLevel(log_level_int)

        if STRUCTLOG_AVAILABLE:
            structlog.configure(
                processors=[
                    structlog.stdlib.filter_by_level,
                    structlog.stdlib.add_logger_name,
                    structlog.stdlib.add_log_level,
                    structlog.stdlib.PositionalArgumentsFormatter(),
                    structlog.processors.TimeStamper(fmt="iso"),
                    structlog.processors.StackInfoRenderer(),
                    structlog.processors.format_exc_info,
                    structlog.processors.UnicodeDecoder(),
                    structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
                ],
                context_class=dict,
                logger_factory=structlog.stdlib.LoggerFactory(),
                cache_logger_on_first_use=True,
            )

        cls._configured = True

    @staticmethod
    def get_logger(name):
        if STRUCTLOG_AVAILABLE:
            return structlog.get_logger(name)
        else:
            return ViaSuiteLoggerAdapter(logging.getLogger(name), {})


def get_logger(name):
    return ViaSuiteLogger.get_logger(name)