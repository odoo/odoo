# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import re


class SensitiveDataFilter(logging.Filter):

    def __init__(self, sensitive_keys):
        super().__init__()
        if sensitive_keys is None:
            self._sensitive_keys = set()
        else:
            self._sensitive_keys = sensitive_keys
        self._compile_patterns()

    def _compile_patterns(self):
        """Precompile regex patterns for all sensitive keys, matching double/single-quoted JSON
        entries.

        :return: None
        """
        self._patterns = []
        for key in self._sensitive_keys:
            # 1st group: "<key>" or '<key>'
            # 2nd group: The quote char for the value
            pattern = re.compile(rf'([\'"]{key}[\'"])\s*:\s*([\'"])([^\'"]+)\2')
            self._patterns.append(pattern)

    def filter(self, record):
        """Override of `logging` to mask any sensitive data in record.args before the record is
        emitted. Always returns True to allow the record through.

        :return: True
        :rtype: bool
        """
        if len(self._patterns) != len(self._sensitive_keys):  # If keys changed.
            self._compile_patterns()  # Recompile the patterns.

        record.args = self._mask(record.args)
        return True

    def _mask(self, data):
        """Recursively mask dicts, iterables, and strings.

        :param data: The data to mask.
        :return: The masked data.
        """
        if isinstance(data, dict):
            masked_dict = {}
            for k, v in data.items():
                masked_dict[k] = "[REDACTED]" if k in self._sensitive_keys else self._mask(v)
            return masked_dict
        if isinstance(data, (list, tuple, set)):
            cls = type(data)
            return cls(self._mask(v) for v in data)
        if isinstance(data, str):
            return self._mask_string(data)
        return data

    def _mask_string(self, text):
        """Apply each pattern, replacing the value with [REDACTED].

        :param str text: The string to mask.
        :return: The masked string.
        :rtype: str
        """
        def replace(m):
            # 1st group: "<key>" or '<key>'
            # 2nd group: The quote char for the value
            quote = m.group(2)
            return f"{m.group(1)}: {quote}[REDACTED]{quote}"

        for pattern in self._patterns:
            text = re.sub(pattern, replace, text)
        return text


def get_payment_logger(name, sensitive_keys=None):
    """Return a logger with a SensitiveDataFilter added if sensitive keys are provided.

    :param str name: The name of the logger.
    :param set sensitive_keys: The keys of the payment data that should not be logged.
    :return: The logger.
    :rtype: logging.Logger
    """
    logger = logging.getLogger(name)
    if sensitive_keys is not None:
        logger.addFilter(SensitiveDataFilter(sensitive_keys))
    return logger
