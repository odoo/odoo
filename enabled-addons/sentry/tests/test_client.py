# Copyright 2016-2017 Versada <https://versada.eu/>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
import sys
from unittest.mock import patch

from sentry_sdk.integrations.logging import _IGNORED_LOGGERS
from sentry_sdk.transport import HttpTransport

from odoo import exceptions
from odoo.tests import TransactionCase
from odoo.tools import config

from ..const import to_int_if_defined
from ..hooks import before_send, initialize_sentry

GIT_SHA = "d670460b4b4aece5915caf5c68d12f560a9fe3e4"
RELEASE = "test@1.2.3"


def remove_handler_ignore(handler_name):
    """Removes handlers of handlers ignored list."""
    _IGNORED_LOGGERS.discard(handler_name)


class TestException(exceptions.UserError):
    pass


class InMemoryTransport(HttpTransport):
    """A :class:`sentry_sdk.Hub.transport` subclass which simply stores events
    in a list.

    Extended based on the one found in raven-python to avoid additional testing
    dependencies: https://git.io/vyGO3
    """

    def __init__(self, *args, **kwargs):
        self.events = []
        self.envelopes = []

    def capture_envelope(self, envelope, *args, **kwargs):
        self.envelopes.append(envelope)

    def has_event(self, event_level, event_msg):
        for envelope in self.envelopes:
            event = envelope.get_event()
            if (
                event.get("level") == event_level
                and event.get("logentry", {}).get("message") == event_msg
            ):
                return event
        return False

    def flush(self, *args, **kwargs):
        pass

    def kill(self, *args, **kwargs):
        pass


class NoopHandler(logging.Handler):
    """
    A Handler subclass that does nothing with any given log record.

    Sentry's log patching works by having the integration process things after
    the normal log handlers are run, so we use this handler to do nothing and
    move to Sentry logic ASAP.
    """

    def emit(self, record):
        pass


class TestClientSetup(TransactionCase):
    def setUp(self):
        super().setUp()
        self.dsn = "http://public:secret@example.com/1"
        self.patch_config(
            {
                "sentry_enabled": True,
                "sentry_dsn": self.dsn,
                "sentry_logging_level": "error",
            }
        )
        self.client = initialize_sentry(config)._client
        self.client.transport = InMemoryTransport({"dsn": self.dsn})

        # Setup our own logger so we don't flood stderr with error logs
        self.logger = logging.getLogger("odoo.sentry.test.logger")
        # Do not mutate list while iterating it
        handlers = [handler for handler in self.logger.handlers]
        for handler in handlers:
            self.logger.removeHandler(handler)
        self.logger.addHandler(NoopHandler())
        self.logger.propagate = False

    def patch_config(self, options: dict):
        """
        Patch Odoo's config with the given `options`, ensuring that the patch
        is undone when the test completes.
        """
        _config_patcher = patch.dict(
            in_dict=config.options,
            values=options,
        )
        _config_patcher.start()
        self.addCleanup(_config_patcher.stop)

    def log(self, level, msg, exc_info=None):
        self.logger.log(level, msg, exc_info=exc_info)

    def assertEventCaptured(self, client, event_level, event_msg):
        self.assertTrue(
            client.transport.has_event(event_level, event_msg),
            msg=f"Event: {event_msg} was not captured",
        )

    def assertEventNotCaptured(self, client, event_level, event_msg):
        self.assertFalse(
            client.transport.has_event(event_level, event_msg),
            msg=f"Event: {event_msg} was captured",
        )

    def test_initialize_raven_sets_dsn(self):
        self.assertEqual(self.client.dsn, self.dsn)

    def test_ignore_low_level_event(self):
        level, msg = logging.WARNING, "Test event, can be ignored"
        self.log(level, msg)
        level = "warning"
        self.assertEventNotCaptured(self.client, level, msg)

    def test_capture_event(self):
        level, msg = logging.ERROR, "Test event, should be captured"
        self.log(level, msg)
        level = "error"
        self.assertEventCaptured(self.client, level, msg)

    def test_capture_event_exc(self):
        level, msg = logging.ERROR, "Test event, can be ignored exception"
        try:
            raise TestException(msg)
        except TestException:
            exc_info = sys.exc_info()
        self.log(level, msg, exc_info)
        level = "error"
        self.assertEventCaptured(self.client, level, msg)

    def test_capture_events_no_tags(self):
        """Our 'before_send' can handle events without tags"""
        level, msg = logging.ERROR, "Test event, can be ignored exception"
        try:
            raise TestException(msg)
        except TestException:
            exc_info = sys.exc_info()
        self.log(level, msg, exc_info)
        level = "error"
        event = self.client.transport.has_event(level, msg)
        self.assertTrue(event)
        # Offer an event without tags to the before_send hook
        if "tags" in event:
            del event["tags"]
        self.assertTrue(before_send(event, {}))

    def test_ignore_exceptions(self):
        self.patch_config(
            {
                "sentry_ignore_exceptions": "odoo.exceptions.UserError",
            }
        )
        client = initialize_sentry(config)._client
        client.transport = InMemoryTransport({"dsn": self.dsn})
        level, msg = logging.ERROR, "Test exception"
        try:
            raise exceptions.UserError(msg)
        except exceptions.UserError:
            exc_info = sys.exc_info()
        self.log(level, msg, exc_info)
        level = "error"
        self.assertEventNotCaptured(client, level, msg)

    def test_capture_exceptions_with_no_exc_info(self):
        """A UserError that isn't in the DEFAULT_IGNORED_EXCEPTIONS list is captured
        (there is no exc_info in the ValidationError exception)."""
        client = initialize_sentry(config)._client
        client.transport = InMemoryTransport({"dsn": self.dsn})
        level, msg = logging.ERROR, "Test exception"

        # Odoo handles UserErrors by logging the exception
        with patch("odoo.addons.sentry.const.DEFAULT_IGNORED_EXCEPTIONS", new=[]):
            self.log(level, exceptions.ValidationError(msg))

        level = "error"
        self.assertEventCaptured(client, level, msg)

    def test_ignore_exceptions_with_no_exc_info(self):
        """A UserError that is in the DEFAULT_IGNORED_EXCEPTIONS is not captured
        (there is no exc_info in the ValidationError exception)."""
        client = initialize_sentry(config)._client
        client.transport = InMemoryTransport({"dsn": self.dsn})
        level, msg = logging.ERROR, "Test exception"

        # Odoo handles UserErrors by logging the exception
        self.log(level, exceptions.ValidationError(msg))

        level = "error"
        self.assertEventNotCaptured(client, level, msg)

    def test_exclude_logger(self):
        self.patch_config(
            {
                "sentry_enabled": True,
                "sentry_exclude_loggers": self.logger.name,
            }
        )
        client = initialize_sentry(config)._client
        client.transport = InMemoryTransport({"dsn": self.dsn})
        level, msg = logging.ERROR, f"Test exclude logger {__name__}"
        self.log(level, msg)
        level = "error"
        # Revert ignored logger so it doesn't affect other tests
        remove_handler_ignore(self.logger.name)
        self.assertEventNotCaptured(client, level, msg)

    def test_invalid_logging_level(self):
        self.patch_config(
            {
                "sentry_logging_level": "foo_bar",
            }
        )
        client = initialize_sentry(config)._client
        client.transport = InMemoryTransport({"dsn": self.dsn})
        level, msg = logging.WARNING, "Test we use the default"
        self.log(level, msg)
        level = "warning"
        self.assertEventCaptured(client, level, msg)

    def test_undefined_to_int(self):
        self.assertIsNone(to_int_if_defined(""))

    @patch("odoo.addons.sentry.hooks.get_odoo_commit", return_value=GIT_SHA)
    def test_config_odoo_dir(self, get_odoo_commit):
        self.patch_config({"sentry_odoo_dir": "/opt/odoo/core"})
        client = initialize_sentry(config)._client

        self.assertEqual(
            client.options["release"],
            GIT_SHA,
            "Failed to use 'sentry_odoo_dir' parameter appropriately",
        )

    @patch("odoo.addons.sentry.hooks.get_odoo_commit", return_value=GIT_SHA)
    def test_config_release(self, get_odoo_commit):
        self.patch_config(
            {
                "sentry_odoo_dir": "/opt/odoo/core",
                "sentry_release": RELEASE,
            }
        )
        client = initialize_sentry(config)._client

        self.assertEqual(
            client.options["release"],
            RELEASE,
            "Failed to use 'sentry_release' parameter appropriately",
        )
