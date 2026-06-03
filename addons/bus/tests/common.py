# Part of Odoo. See LICENSE file for full copyright and licensing details.

import contextlib
import inspect
import json
import struct
import unittest
from itertools import chain, zip_longest
from threading import Event
from unittest.mock import patch

from werkzeug.exceptions import BadRequest

try:
    import websocket
except ImportError:
    websocket = None

from odoo.http import request
from odoo.tests import HttpCase
from odoo.tests.common import (
    HOST,
    TEST_CURSOR_COOKIE_NAME,
    BaseCase,
    Like,
    _registry_test_lock,
    release_test_lock,
)

from odoo.addons.bus.models.bus import BusBus, channel_with_db, json_dump
from odoo.addons.bus.tools import encode_snapshot
from odoo.addons.bus.websocket import CloseCode, Websocket, WebsocketConnectionHandler


class MockBusTransaction:
    """A simulated bus transaction handed out by :class:`MockBusTransactions`.

    Use as a context manager (commits on __exit__) or manually via :meth:`commit` to hold
    several transactions open concurrently and commit them in a controlled order.
    """

    def __init__(self, parent: "MockBusTransactions", xid: int, cr):
        self._parent = parent
        self._xid = xid
        self._cr = cr
        self._pending = []

    def __enter__(self):
        assert self._parent._current_tx is None, "Nested transactions are forbidden."
        self._parent._current_tx = self
        return self

    def __exit__(self, exc_type, *args):
        try:
            if not exc_type:
                self.commit()
        finally:
            self._parent._current_tx = None

    def send(self, channel, type_, payload=None, *, subchannel=None):
        assert self._xid in self._parent._active_xids, "Cannot send on a committed transaction."
        self._pending.append((channel, type_, payload, subchannel))
        return self

    def commit(self):
        assert self._xid in self._parent._active_xids, "Transaction cannot be committed twice."
        assert self._parent._current_tx in (None, self), "Nested transactions are forbidden."
        bus = self._cr.transaction.default_env["bus.bus"]
        for channel, type_, payload, subchannel in self._pending:
            actual_channel = (channel, subchannel) if subchannel else channel
            bus._sendone(actual_channel, type_, payload)
        self._pending.clear()
        self._parent._current_tx = self
        self._parent._active_xids.remove(self._xid)
        self._cr.precommit.run()
        self._cr.postcommit.run()
        self._parent._current_tx = None


class MockBusTransactions:
    """Simulate PostgreSQL MVCC behavior the bus relies on.

    Real bus dispatching depends on transaction xids and visibility snapshots to decide
    which notification should be delivered to subscribers. Testing that logic with the
    actual database would require multiple concurrent connections. This class fakes it
    instead by handing out :class:`MockBusTransaction` objects with controlled xids and
    serving a matching `pg_current_snapshot`.

    The bus dispatching code itself (:meth:`~models.bus.fetch_bus_notifications` Websocket
    state) remains intact.
    """

    def __init__(self, initial_xid: int, cr):
        self._next_xid = initial_xid
        self._active_xids = []
        self._current_tx = None
        self._cr = cr

    def snapshot(self):
        xmin = min(self._active_xids) if self._active_xids else self._next_xid
        xip = ",".join(map(str, sorted(self._active_xids)))
        return encode_snapshot(f"{xmin}:{self._next_xid}:{xip}")

    def tx(self, cr=None):
        xid = self._next_xid
        self._next_xid += 1
        self._active_xids.append(xid)
        return MockBusTransaction(self, xid, cr or self._cr)


@contextlib.contextmanager
def mock_bus_transactions(cr):
    """Patch bus snapshot/xid to use a :class:`MockBusTransactions` mock.

    Yields the :class:`MockBusTransactions` instance controlling the simulated MVCC state.
    Bus rows get their ``create_xid`` from a SQL DEFAULT (``pg_current_xact_id()``). The
    wrapped ``create`` injects the simulated xid so the fixture controls the value instead
    of Postgres.
    """
    cr.execute("SELECT pg_current_xact_id()")
    bus_db_mock = MockBusTransactions(int(cr.fetchone()[0]) + 1, cr)
    original_create = BusBus.create

    def _mocked_create(records, vals_list):
        if (tx := bus_db_mock._current_tx) is not None:
            for vals in vals_list:
                vals["create_xid"] = tx._xid
        return original_create(records, vals_list)

    with (
        patch.object(BusBus, "get_current_pg_snapshot", side_effect=lambda _: bus_db_mock.snapshot()),
        patch("odoo.addons.bus.models.bus.BusBus.create", _mocked_create),
    ):
        yield bus_db_mock


class BusResult:
    """Descriptor for an expected bus notification.
    :param channel: the bus channel
    :param str type: the notification type
    :param payload: the notification payload
    When a payload dict is provided, only the specified keys and values are
    checked against the actual notification; extra keys in the actual payload
    are ignored.
    """

    def __init__(self, channel, type=None, payload=None):
        self.channel = channel
        self.type = type
        self.payload = payload.as_dict() if hasattr(payload, "as_dict") else payload
        self.matched = False
        self.misordered_matched = False
        self.wrong_order_expected_idx = None
        self.wrong_order_received_idx = None

    def _check_match(self, received, *, show_store_versioning):
        """Return whether notifications match without mutating state."""
        return (
            self._normalized_channel() == received._normalized_channel()
            and (self.type is None or self.type == received.type)
            and (
                self.payload is None
                or self._normalized_message(show_store_versioning=show_store_versioning)
                == received._normalized_message(show_store_versioning=show_store_versioning)
            )
        )

    def match(self, received, *, show_store_versioning):
        if self._check_match(received, show_store_versioning=show_store_versioning):
            self.matched = True
            received.matched = True
            return True
        return False

    def misordered_match_idx(self, notifications, *, show_store_versioning):
        with contextlib.suppress(StopIteration):
            res = next(
                idx
                for idx, notification in enumerate(notifications, 1)
                if (not notification.matched and not notification.misordered_matched)
                and self._check_match(notification, show_store_versioning=show_store_versioning)
            )
            notifications[res - 1].misordered_matched = True
            return res
        return None

    def format_log(self, idx, *, show_store_versioning):
        if self.wrong_order_received_idx is not None:
            status = f"⚠️ wrong order: expected #{idx} -> received #{self.wrong_order_received_idx}"
        elif self.wrong_order_expected_idx is not None:
            status = f"⚠️ wrong order: received #{idx} -> expected #{self.wrong_order_expected_idx}"
        elif self.matched:
            status = f"✅ matched #{idx}"
        else:
            status = f"❌ missing #{idx}"
        channel, type_, payload = self.to_tuple(show_store_versioning=show_store_versioning)
        return (
            f"# {status}\n"
            "(\n"
            f"    {json_dump(channel)},\n"
            f"    {json_dump(type_)},\n"
            f"    {json_dump(payload)},\n"
            "),"
        )

    def to_tuple(self, *, show_store_versioning):
        payload = json.loads(json_dump(self.payload)) if self.payload is not None else None
        if not show_store_versioning:
            BusResult._pop_store_version(payload)
        return (self._normalized_channel(), self.type, payload)

    @staticmethod
    def _pop_store_version(data):
        if not isinstance(data, dict):
            return
        data.pop("__store_version__", False)
        for value in data.values():
            BusResult._pop_store_version(value)

    def _normalized_channel(self):
        if isinstance(self.channel, str):
            return tuple(json.loads(self.channel))
        return tuple(self.channel)

    def _normalized_message(self, *, show_store_versioning):
        message = {}
        if self.type is not None:
            message["type"] = self.type
        if self.payload is not None:
            message["payload"] = self.payload
            if not show_store_versioning:
                BusResult._pop_store_version(message["payload"])
        return json.loads(json_dump(message)) if message else None


class BusCase(BaseCase):
    def _reset_bus(self):
        self.env.cr.precommit.data.get("bus.bus.values", []).clear()
        if channel_set := self.env.cr.postcommit.data.get("bus.bus.channels"):
            channel_set.clear()
        self.env["bus.bus"].sudo().search([]).unlink()

    @contextlib.contextmanager
    def assertBus(self, notifications, *, show_store_versioning=False):
        """Check content of bus notifications.

        `notifications` is a :class:`BusResult` instance or a list of them, e.g.:

            BusResult(self.user_employee, "mail.record/insert", {...})
            BusResult(self.user_employee)
            BusResult(self.user_employee, "mail.message/inbox")
            BusResult(self.user_employee, payload={"key": val})
            BusResult(self.user_employee, "mail.record/insert", {"key": val})

        A single :class:`BusResult` may be passed directly instead of a one-element list.
        Notifications are matched in emitted order.
        `notifications` may be either a :class:`BusResult`, a list of them,
        or a callable evaluated after the tested code that returns one of
        those forms.
        """
        self._reset_bus()
        yield
        self._assertBusNotifications(notifications, show_store_versioning=show_store_versioning)

    def _assertBusNotifications(self, notifications, *, show_store_versioning=False):
        """Assert bus notifications with coupled channel and message.

        :param notifications: expected notifications as :class:`BusResult`, list,
            or callable returning one of those forms.

        Expected notifications must appear in order.
        """
        self.maxDiff = None
        notifications = notifications() if callable(notifications) else notifications
        if isinstance(notifications, BusResult):
            notifications = [notifications]
        notifications = notifications or []
        self.env.cr.precommit.run()  # trigger the creation of bus.bus records
        expected_list = []
        for notif in notifications:
            if not isinstance(notif, BusResult):
                msg = "Bus: expected notification items must be a BusResult instance."
                raise TypeError(msg)
            expected_list.append(
                BusResult(
                    json_dump(channel_with_db(self.cr.dbname, notif.channel)),
                    notif.type,
                    notif.payload,
                ),
            )
        received_list = [
            BusResult(notif.channel, **json.loads(notif.message))
            for notif in self.env["bus.bus"].sudo().search([])
        ]
        for expected_notif, actual_notif in zip_longest(expected_list, received_list):
            if expected_notif is not None and actual_notif is not None:
                expected_notif.match(actual_notif, show_store_versioning=show_store_versioning)
        for expected in (e for e in expected_list if not e.matched):
            expected.wrong_order_received_idx = expected.misordered_match_idx(
                received_list,
                show_store_versioning=show_store_versioning,
            )
        for received in (e for e in received_list if not e.matched):
            received.wrong_order_expected_idx = received.misordered_match_idx(
                expected_list,
                show_store_versioning=show_store_versioning,
            )
        if any(not notif.matched for notif in chain(expected_list, received_list)):

            def format_notifications(title, notifications):
                error_parts.append(title)
                if notifications:
                    for idx, notif in enumerate(notifications, 1):
                        error_parts.append(
                            notif.format_log(idx, show_store_versioning=show_store_versioning),
                        )
                else:
                    error_parts.append("<no notifications>")

            error_parts = ["Bus notifications."]
            format_notifications("\nExpected notifications:", expected_list)
            format_notifications("\nReceived notifications:", received_list)
            for idx, (expected, actual) in enumerate(zip_longest(expected_list, received_list), 1):
                with self.subTest(idx=idx):
                    if expected is not None and actual is not None and not expected.matched:
                        self.assertEqual(
                            expected.to_tuple(show_store_versioning=show_store_versioning),
                            actual.to_tuple(show_store_versioning=show_store_versioning),
                            f"\n❌ mismatch at comparison #{idx}",
                        )
            raise AssertionError("\n".join(error_parts))


class WebsocketCase(HttpCase, BusCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if websocket is None:
            cls._logger.warning("websocket-client module is not installed")
            raise unittest.SkipTest("websocket-client module is not installed")
        cls._BASE_WEBSOCKET_URL = f"ws://{HOST}:{cls.http_port()}/websocket"
        cls._WEBSOCKET_URL = f"{cls._BASE_WEBSOCKET_URL}?version={WebsocketConnectionHandler._VERSION}"
        websocket_allowed_patch = patch.object(WebsocketConnectionHandler, "websocket_allowed", return_value=True)
        cls.startClassPatcher(websocket_allowed_patch)

    def setUp(self):
        super().setUp()
        self._reset_bus()
        self._websockets = set()
        # Used to ensure websocket connections have been closed
        # properly.
        self._websocket_events = set()
        original_serve_forever = WebsocketConnectionHandler._serve_forever

        def _mocked_serve_forever(*args):
            websocket_closed_event = Event()
            self._websocket_events.add(websocket_closed_event)
            original_serve_forever(*args)
            websocket_closed_event.set()

        self._serve_forever_patch = patch.object(
            WebsocketConnectionHandler,
            '_serve_forever',
            wraps=_mocked_serve_forever
        )
        self.startPatcher(self._serve_forever_patch)
        self.enterContext(release_test_lock())  # Release the lock during websocket tests
        self.http_request_key = 'websocket'
        self.bus_db_mock = self.enterContext(mock_bus_transactions(self.env.cr))

    def tearDown(self):
        self._close_websockets()
        super().tearDown()

    def _close_websockets(self):
        """
        Close all the connected websockets and wait for the connection
        to terminate.
        """
        for ws in self._websockets:
            if ws.connected:
                ws.close(CloseCode.CLEAN)
        self.wait_remaining_websocket_connections()

    @contextlib.contextmanager
    def allow_requests(self, *args, **kwargs):
        # As the lock is always unlocked, we reacquire it before allowing request
        # to avoid exceptions.
        with _registry_test_lock, super().allow_requests(*args, **kwargs):
            yield

    def assertCanOpenTestCursor(self):
        # As the lock is always unlocked during WebsocketCases we have a whitelist of
        # methods which must match. We also default to super if we are coming from a cursor.
        allowed_methods = [  # function + filename
            ('acquire_cursor', Like('.../bus/websocket.py')),
        ]
        if any(
            frame.function == function and frame.filename == filename
            for frame in inspect.stack()
            for function, filename in allowed_methods
        ) or request:
            return super().assertCanOpenTestCursor()
        raise BadRequest('Opening a cursor from an unknown method in websocket test.')

    def websocket_connect(self, *args, ping_after_connect=True, **kwargs):
        """
        Connect a websocket. If no cookie is given, the connection is
        opened with a default session. The created websocket is closed
        at the end of the test.
        """
        if 'cookie' not in kwargs:
            self.session = self.authenticate(None, None)
            kwargs['cookie'] = f'session_id={self.session.sid}'
        kwargs['timeout'] = 10  # keep a large timeout to avoid aving a websocket request escaping the test
        # The cursor lock is already released, we just need to pass the right cookie.
        kwargs['cookie'] += f';{TEST_CURSOR_COOKIE_NAME}={self.http_request_key}'
        ws = websocket.create_connection(
            self._WEBSOCKET_URL, *args, **kwargs
        )
        if ping_after_connect:
            ws.ping()
            ws.recv_data_frame(control_frame=True)  # pong
        self._websockets.add(ws)
        return ws

    def subscribe(
        self,
        websocket,
        channels=None,
        check_outdated=False,
        from_snapshot=None,
        wait_for_dispatch=True,
    ):
        """ Subscribe the websocket to the given channels.

        :param websocket: The websocket of the client.
        :param channels: The list of channels to subscribe to.
        :param last: The last notification id the client received.
        :param check_outdated: Whether the websocket should check if the from_snapshot
            still exists in the bus table. Used to detect GC of the bus table during
            disconnect.
        :param from_snapshot: The starting point of the notification dispatching for the
            added channels.
        :param wait_for_dispatch: Whether to wait for the notification dispatching
            trigerred by the subscription.
        """
        dispatch_bus_notification_done = Event()
        original_dispatch_bus_notifications = Websocket._dispatch_bus_notifications

        def _mocked_dispatch_bus_notifications(self, *args):
            original_dispatch_bus_notifications(self, *args)
            dispatch_bus_notification_done.set()

        with patch.object(Websocket, '_dispatch_bus_notifications', _mocked_dispatch_bus_notifications):
            sub = {'event_name': 'subscribe', 'data': {
                'channels': channels or [],
                'check_outdated': check_outdated,
            }}
            if not from_snapshot:
                from_snapshot = self.bus_db_mock.snapshot()
            sub["data"]["from_snapshot"] = from_snapshot
            websocket.send(json.dumps(sub))
            if wait_for_dispatch:
                dispatch_bus_notification_done.wait(timeout=5)

    def wait_remaining_websocket_connections(self):
        """ Wait for the websocket connections to terminate. """
        for event in self._websocket_events:
            event.wait(5)

    def assert_close_with_code(self, websocket, expected_code, expected_reason=None):
        """
        Assert that the websocket is closed with the expected_code.
        """
        opcode, payload = websocket.recv_data()
        if opcode != 8:
            opcode_txt = {0: "continuation", 1: "text", 2: "binary", 9: "ping", 0xA: "pong"}[opcode]
            details = f": {payload.decode('utf-8', errors='replace')}" if opcode == 1 else ""
            self.fail(f"Expected close frame, got {opcode_txt} frame{details}")
        code = struct.unpack('!H', payload[:2])[0]
        # ensure the close code is the one we expected
        self.assertEqual(code, expected_code)
        if expected_reason:
            # ensure the close reason is the one we expected
            self.assertEqual(payload[2:].decode(), expected_reason)
