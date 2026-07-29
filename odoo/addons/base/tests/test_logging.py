import json
import logging
import sys

from odoo.logging import JSONFormatter
from odoo.tests.common import BaseCase


class TestJsonFormatter(BaseCase):
    def setUp(self):
        super().setUp()
        self.record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg='test message',
            args=(),
            exc_info=None,
        )

    def test_json_formatter(self):
        formatter = JSONFormatter()
        formatted = json.loads(formatter.format(self.record))
        keys = set(formatted.keys())

        # an assert equal could work but we don't want to be to rigid on case keys are added, we want to ensure that
        # - default ignore_record_keys works as expected
        # - test is always present and correct
        unexpected_keys = {'msecs', 'relativeCreated', 'asctime'} & keys
        self.assertFalse(unexpected_keys, f"Unexpected keys found: {sorted(unexpected_keys)}")
        missing_keys = {'created', 'message', 'test'} - keys
        self.assertFalse(missing_keys, f"Expected keys missing: {sorted(missing_keys)}")
        self.assertEqual(formatted['test']['canonical_tag'], '/base/tests/test_logging.py:TestJsonFormatter.test_json_formatter')

    def test_defined_record_keys(self):
        formatter = JSONFormatter(record_keys=['name', 'levelname', 'message', 'test'])
        formatted = json.loads(formatter.format(self.record))
        keys = sorted(formatted.keys())
        expected_keys = ['levelname', 'message', 'name', 'test']

        self.assertEqual(keys, expected_keys, f"Expected keys: {sorted(expected_keys)}, got: {sorted(keys)}")

    def test_tweak_record_keys(self):
        formatter = JSONFormatter(ignore_record_keys=['created'], additional_record_keys=['asctime'])
        formatted = json.loads(formatter.format(self.record))
        keys = set(formatted.keys())

        unexpected_keys = {'created'} & keys
        self.assertFalse(unexpected_keys, f"Unexpected keys found: {sorted(unexpected_keys)}")
        missing_keys = {'asctime', 'message', 'test'} - keys
        self.assertFalse(missing_keys, f"Expected keys missing: {sorted(missing_keys)}")

    def test_exc_info_included(self):
        try:
            raise ValueError("Test exception")  # noqa: EM101, TRY301
        except ValueError:
            self.record.exc_info = sys.exc_info()
            formatter = JSONFormatter()
            formatted = json.loads(formatter.format(self.record))
            self.assertIn('Traceback', formatted.get('exc_info'), "Expected 'exc_info' key in formatted output")

    def test_no_ignored_keys(self):
        # The previous behaviour was to be able to set ignored_record_keys to an empty list to include all keys,
        # but this makes the implementation and usage confusing
        # This test show that it is still possible to include all keys by using additional_record_keys with the default ignored keys
        formatter = JSONFormatter(additional_record_keys=JSONFormatter.DEFAULT_IGNORED_RECORD_KEYS)
        formatted = json.loads(formatter.format(self.record))
        missing_keys = {'msecs', 'relativeCreated'} - set(formatted.keys())
        self.assertFalse(missing_keys, f"Expected keys missing: {sorted(missing_keys)}")
