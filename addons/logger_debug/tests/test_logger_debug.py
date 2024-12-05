
import logging

from odoo.addons.logger_debug.tools.log_filter_debug import LogFilterDebugDB
from odoo.tests import BaseCase, tagged


@tagged('-at_install', 'post_install')
class TestLogFilterDebugDB(BaseCase):
    def setUp(self):
        super().setUp()
        self.log_filter_debug_db = LogFilterDebugDB()

    def test_filter_basic(self):
        logger_name = "test_dummy_logger"
        logger = logging.getLogger(logger_name)

        # Test normal logging behavior
        with self.assertLogs(logger_name, logging.INFO) as cm:
            logger.info("info message")
            logger.debug("debug message")
        self.assertEqual(cm.output, ["INFO:test_dummy_logger:info message"])

        with self.assertLogs(logger_name, logging.DEBUG) as cm:
            logger.info("info message")
            logger.debug("debug message")
        self.assertEqual(cm.output, ["INFO:test_dummy_logger:info message", "DEBUG:test_dummy_logger:debug message"])

        # We add our debug filter to the logger
        # Currently there is no database set, so the filter should not filter out any debug messages
        logger.addFilter(self.log_filter_debug_db)
        with self.assertLogs(logger_name, logging.DEBUG) as cm:
            logger.info("info message")
            logger.debug("debug message")
        self.assertEqual(cm.output, ["INFO:test_dummy_logger:info message"])

        # We add our database to the filter, now it should log the debug message
        self.log_filter_debug_db.add_logger(logger_name)
        with self.assertLogs(logger_name, logging.DEBUG) as cm:
            logger.info("info message")
            logger.debug("debug message")
        self.assertEqual(cm.output, ["INFO:test_dummy_logger:info message", "DEBUG:test_dummy_logger:debug message"])

        # Test logger inheritance
        # inherited_logger_name = logger_name + ".foo"
        # inherited_logger = logging.getLogger(inherited_logger_name)
        # with self.assertLogs(inherited_logger_name, logging.DEBUG) as cm:
        #     inherited_logger.info("info message 2")
        #     inherited_logger.debug("debug message 2")
        # self.assertEqual(cm.output, ["INFO:test_dummy_logger.foo:info message", "DEBUG:test_dummy_logger.foo:debug message"])

    #TODO: add a test with logger removed
    #TODO: add a test with multiple databases (by just hardcoding the dbname in the thread to something else ?)
