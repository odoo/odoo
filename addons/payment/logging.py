import logging
import re


class SensitiveDataFilter(logging.Filter):

    def __init__(self, name='', sensitive_keys=None):
        super().__init__(name)
        if sensitive_keys is None:
            self._sensitive_keys = set()
        else:
            self._sensitive_keys = sensitive_keys
        self._compile_patterns()

    def _compile_patterns(self):
        """Precompile regex patterns for all keys in SENSITIVE_KEYS,
        matching double/single-quoted JSON entries.
        :return: None
        """
        self._patterns = []
        for key in self._sensitive_keys:
            # group1: "key" or 'key'
            # group2: the quote char for the value
            pattern = re.compile(rf"(['\"]{key}['\"])\s*:\s*(['\"])([^'\"]+)\2")
            self._patterns.append(pattern)

    def filter(self, record):
        """
        Called by the logging framework. Masks any configured sensitive data in record.args before
        the record is emitted. Always returns True to allow the record through.
        """
        if len(self._patterns) != len(self._sensitive_keys):  # If keys changed
            self._compile_patterns()  # Recompile
        record.args = self._mask(record.args)
        return True

    def _mask(self, data):
        """Recursively mask dicts, iterables, and strings.

        :param data: The data to mask.
        :return: The masked data.
        """
        if isinstance(data, dict):
            return {
                k: ("******" if k in self._sensitive_keys else self._mask(v))
                for k, v in data.items()
            }
        if isinstance(data, (list, tuple, set)):
            cls = type(data)
            return cls(self._mask(v) for v in data)
        if isinstance(data, str):
            return self._mask_string(data)
        return data

    def _mask_string(self, text):
        """Apply each pattern, replacing the value with ******.

        :param str text: The string to mask.
        :return: The masked string.
        :rtype: str
        """
        def repl(m):
            # m.group(1) is the quoted key, m.group(2) is the quote used for the value
            quote = m.group(2)
            return f"{m.group(1)}: {quote}******{quote}"
        for pattern in self._patterns:
            text = re.sub(pattern, repl, text)
        return text


def get_payment_logger(name, sensitive_keys=None):
    """Return a logger with a SensitiveDataFilter added if sensitive_keys are provided.

    :param name: The name of the logger.
    :param sensitive_keys: The keys that are sensitive and should not be logged.
    :return: The logger.
    :rtype: logging.Logger
    """
    logger = logging.getLogger(name)
    if sensitive_keys is not None:
        logger.addFilter(SensitiveDataFilter(sensitive_keys=sensitive_keys))
    return logger
