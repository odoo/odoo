import logging
import unittest
import unittest.mock

from odoo.libs.asset_log import get_asset_logger, log_event


class TestLogEvent(unittest.TestCase):
    def test_a_value_with_spaces_stays_one_field(self):
        logger = get_asset_logger("test")
        with self.assertLogs(logger, logging.WARNING) as logged:
            log_event(
                logger, logging.WARNING, "failed", error="exit 1: no such file", ms=12.5
            )
        self.assertEqual(
            logged.records[0].getMessage(),
            "event=failed error='exit 1: no such file' ms=12.500",
        )

    def test_plain_values_read_as_before(self):
        logger = get_asset_logger("test")
        with self.assertLogs(logger, logging.INFO) as logged:
            log_event(
                logger, logging.INFO, "started", bundle="web.assets_web", modules=42
            )
        self.assertEqual(
            logged.records[0].getMessage(),
            "event=started bundle=web.assets_web modules=42",
        )

    def test_a_disabled_level_formats_nothing(self):
        logger = get_asset_logger("test_quiet")
        logger.setLevel(logging.ERROR)
        with unittest.mock.patch.object(logger, "log") as log:
            log_event(logger, logging.INFO, "started")
        log.assert_not_called()
